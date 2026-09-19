"""Versioned SQLite foundation shared by authentication and comment review."""

import sqlite3
import time
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator


class Database:
    def __init__(self, path: Path):
        self.path = path.resolve()

    @contextmanager
    def connect(self) -> Iterator[sqlite3.Connection]:
        connection = sqlite3.connect(self.path, timeout=5)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys=ON")
        try:
            with connection:
                yield connection
        finally:
            connection.close()

    def initialize(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            version = connection.execute("PRAGMA user_version").fetchone()[0]
            if version not in (0, 1, 2, 3, 4, 5):
                raise RuntimeError("Unsupported database schema version")
            if version == 5:
                return
            comment_columns = self._columns(connection, "comments")
            if version in (1, 2, 3) and "comment_id" in comment_columns:
                if version == 1 and not self._table_exists(connection, "sessions"):
                    self._create_auth_support_schema(connection)
                self._migrate_legacy_queue(connection)
                version = 2
            elif version == 3 and "id" not in self._columns(connection, "comments"):
                raise RuntimeError("Unsupported database schema version 3 shape")
            if version == 0:
                self._create_auth_schema(connection)
            if version in (0, 1):
                self._create_review_schema(connection)
            if version in (0, 1, 2):
                self._create_supervision_schema(connection)
                self._migrate_audit_events(connection)
            if version < 4:
                connection.execute("""ALTER TABLE assignments ADD COLUMN return_status TEXT
                    NOT NULL DEFAULT 'PENDING' CHECK (return_status IN
                        ('PENDING', 'ESCALATED', 'REOPENED'))""")
            comment_columns = self._columns(connection, "comments")
            if "uncertainty" not in comment_columns:
                connection.execute("""ALTER TABLE comments ADD COLUMN uncertainty REAL
                    NOT NULL DEFAULT 1 CHECK (uncertainty BETWEEN 0 AND 1)""")
            if "score_source" not in comment_columns:
                connection.execute("""ALTER TABLE comments ADD COLUMN score_source TEXT
                    NOT NULL DEFAULT 'SIMULATED' CHECK (score_source IN ('SIMULATED', 'MODEL'))""")
            connection.execute("PRAGMA user_version=5")

    @staticmethod
    def _columns(connection: sqlite3.Connection, table: str) -> set[str]:
        return {row[1] for row in connection.execute(f"PRAGMA table_info({table})")}

    @staticmethod
    def _table_exists(connection: sqlite3.Connection, table: str) -> bool:
        return connection.execute(
            "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (table,)
        ).fetchone() is not None

    @classmethod
    def _migrate_legacy_queue(cls, connection: sqlite3.Connection) -> None:
        """Copy the dev queue into the reviewed schema within one transaction."""
        from app.comments.scoring import SimulatedScorer

        rows = connection.execute("SELECT * FROM comments ORDER BY sequence").fetchall()
        connection.execute("DROP INDEX IF EXISTS comments_queue")
        connection.execute("DROP INDEX IF EXISTS comments_status_order")
        connection.execute("ALTER TABLE comments RENAME TO legacy_queue_comments")
        cls._create_review_schema(connection)
        claimed_at = int(time.time())
        scorer = SimulatedScorer()
        for row in rows:
            keys = set(row.keys())
            migrated_status = (
                "PENDING"
                if row["status"] == "IN_REVIEW" and not row["assignee_id"]
                else row["status"]
            )
            if "risk_score" in keys and row["risk_score"] is not None:
                risk_score = row["risk_score"]
                uncertainty = row["uncertainty"]
                model_version = row["model_version"]
                score_source = row["score_source"]
            else:
                score = scorer.score_comment(row["text"])
                risk_score, uncertainty = score.risk_score, score.uncertainty
                model_version, score_source = score.model_version, score.score_source
            connection.execute("""INSERT INTO comments
                (id, video_id, text, risk_score, uncertainty, model_version,
                 score_source, source_order, status)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""", (
                row["comment_id"], row["video_id"], row["text"], risk_score,
                uncertainty, model_version, score_source, row["sequence"], migrated_status,
            ))
            if row["assignee_id"] and row["status"] == "IN_REVIEW":
                connection.execute("""INSERT INTO assignments
                    (comment_id, reviewer_id, claimed_at, expires_at)
                    VALUES (?, ?, ?, ?)""", (
                        row["comment_id"], row["assignee_id"], claimed_at, claimed_at + 900,
                    ))
            elif row["assignee_id"]:
                connection.execute("""INSERT INTO assignments
                    (comment_id, reviewer_id, claimed_at, expires_at, closed_at)
                    VALUES (?, ?, 0, 1, 1)""", (row["comment_id"], row["assignee_id"]))
        connection.execute("DROP TABLE legacy_queue_comments")

    @staticmethod
    def _create_auth_schema(connection: sqlite3.Connection) -> None:
        connection.execute("""
                CREATE TABLE users (
                    id TEXT PRIMARY KEY NOT NULL,
                    username TEXT NOT NULL UNIQUE,
                    display_name TEXT NOT NULL,
                    password_hash TEXT NOT NULL,
                    role TEXT NOT NULL CHECK (role IN ('MODERATOR', 'SUPERVISOR')),
                    is_active INTEGER NOT NULL DEFAULT 1 CHECK (is_active IN (0, 1)),
                    created_at INTEGER NOT NULL
                )
        """)
        connection.execute("""
                CREATE TABLE sessions (
                    token_hash TEXT PRIMARY KEY NOT NULL CHECK (length(token_hash) = 64),
                    user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                    created_at INTEGER NOT NULL,
                    expires_at INTEGER NOT NULL CHECK (expires_at > created_at)
                )
        """)
        connection.execute("CREATE INDEX sessions_expiry ON sessions(expires_at)")
        connection.execute("CREATE INDEX sessions_user ON sessions(user_id)")
        connection.execute("""
                CREATE TABLE login_attempts (
                    username TEXT PRIMARY KEY NOT NULL,
                    attempts INTEGER NOT NULL CHECK (attempts > 0),
                    window_started_at INTEGER NOT NULL
                )
        """)
        connection.execute("CREATE INDEX attempts_window ON login_attempts(window_started_at)")

    @staticmethod
    def _create_auth_support_schema(connection: sqlite3.Connection) -> None:
        connection.execute("""CREATE TABLE sessions (
            token_hash TEXT PRIMARY KEY NOT NULL CHECK (length(token_hash) = 64),
            user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            created_at INTEGER NOT NULL,
            expires_at INTEGER NOT NULL CHECK (expires_at > created_at))""")
        connection.execute("CREATE INDEX sessions_expiry ON sessions(expires_at)")
        connection.execute("CREATE INDEX sessions_user ON sessions(user_id)")
        connection.execute("""CREATE TABLE login_attempts (
            username TEXT PRIMARY KEY NOT NULL, attempts INTEGER NOT NULL CHECK (attempts > 0),
            window_started_at INTEGER NOT NULL)""")
        connection.execute("CREATE INDEX attempts_window ON login_attempts(window_started_at)")

    @staticmethod
    def _create_persistence_schema(connection: sqlite3.Connection) -> None:
        """Build the historic queue schema for migration fixtures."""
        connection.execute("""CREATE TABLE users (
            id TEXT PRIMARY KEY NOT NULL, username TEXT NOT NULL UNIQUE,
            display_name TEXT NOT NULL, password_hash TEXT NOT NULL,
            role TEXT NOT NULL CHECK (role IN ('MODERATOR', 'SUPERVISOR')),
            is_active INTEGER NOT NULL DEFAULT 1 CHECK (is_active IN (0, 1)),
            created_at INTEGER NOT NULL)""")
        connection.execute("""CREATE TABLE comments (
            sequence INTEGER PRIMARY KEY AUTOINCREMENT,
            comment_id TEXT NOT NULL UNIQUE, video_id TEXT NOT NULL, text TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'PENDING' CHECK (status IN
                ('PENDING', 'IN_REVIEW', 'CLASSIFIED', 'ESCALATED', 'RESOLVED',
                 'REOPEN_REQUESTED', 'REOPENED')),
            assignee_id TEXT REFERENCES users(id) ON DELETE RESTRICT)""")
        connection.execute("CREATE INDEX comments_status_order ON comments(status, sequence)")

    @staticmethod
    def _create_review_schema(connection: sqlite3.Connection) -> None:
        connection.execute("""
            CREATE TABLE comments (
                id TEXT PRIMARY KEY NOT NULL,
                video_id TEXT NOT NULL,
                text TEXT NOT NULL,
                risk_score REAL NOT NULL CHECK (risk_score BETWEEN 0 AND 1),
                uncertainty REAL NOT NULL DEFAULT 1 CHECK (uncertainty BETWEEN 0 AND 1),
                model_version TEXT NOT NULL,
                score_source TEXT NOT NULL DEFAULT 'SIMULATED'
                    CHECK (score_source IN ('SIMULATED', 'MODEL')),
                source_order INTEGER NOT NULL UNIQUE CHECK (source_order >= 0),
                status TEXT NOT NULL DEFAULT 'PENDING' CHECK (status IN
                    ('PENDING', 'IN_REVIEW', 'CLASSIFIED', 'ESCALATED',
                     'RESOLVED', 'REOPEN_REQUESTED', 'REOPENED'))
            )
        """)
        connection.execute("CREATE INDEX comments_queue ON comments(status, risk_score DESC, source_order)")
        connection.execute("""
            CREATE TABLE assignments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                comment_id TEXT NOT NULL REFERENCES comments(id) ON DELETE RESTRICT,
                reviewer_id TEXT NOT NULL REFERENCES users(id) ON DELETE RESTRICT,
                claimed_at INTEGER NOT NULL,
                expires_at INTEGER NOT NULL CHECK (expires_at > claimed_at),
                closed_at INTEGER
            )
        """)
        connection.execute("""
            CREATE UNIQUE INDEX one_active_assignment
            ON assignments(comment_id) WHERE closed_at IS NULL
        """)
        connection.execute("CREATE INDEX assignments_expiry ON assignments(expires_at) WHERE closed_at IS NULL")
        connection.execute("""
            CREATE TABLE reviews (
                id TEXT PRIMARY KEY NOT NULL,
                assignment_id INTEGER NOT NULL UNIQUE REFERENCES assignments(id),
                comment_id TEXT NOT NULL REFERENCES comments(id) ON DELETE RESTRICT,
                reviewer_id TEXT NOT NULL REFERENCES users(id) ON DELETE RESTRICT,
                reviewer_display_name TEXT NOT NULL,
                result TEXT NOT NULL CHECK (result IN
                    ('NO_ESCALATION', 'ESCALATE_TO_SUPERVISOR',
                     'INSUFFICIENT_CONTEXT', 'TRANSFER_REQUESTED')),
                reason TEXT NOT NULL CHECK (length(trim(reason)) BETWEEN 1 AND 1000),
                created_at INTEGER NOT NULL,
                model_score REAL NOT NULL CHECK (model_score BETWEEN 0 AND 1),
                model_version TEXT NOT NULL
            )
        """)
        connection.execute("CREATE INDEX reviews_comment ON reviews(comment_id, created_at)")
        connection.execute("""
            CREATE TABLE audit_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                comment_id TEXT NOT NULL REFERENCES comments(id) ON DELETE RESTRICT,
                actor_id TEXT,
                actor_display_name TEXT,
                event_type TEXT NOT NULL CHECK (event_type IN
                    ('assigned', 'claim_expired', 'content_revealed',
                     'classified', 'escalated')),
                created_at INTEGER NOT NULL,
                review_id TEXT REFERENCES reviews(id)
            )
        """)
        connection.execute("CREATE INDEX audit_comment ON audit_events(comment_id, id)")

    @staticmethod
    def _create_supervision_schema(connection: sqlite3.Connection) -> None:
        connection.execute("""
            CREATE TABLE reopen_requests (
                id TEXT PRIMARY KEY NOT NULL,
                comment_id TEXT NOT NULL REFERENCES comments(id) ON DELETE RESTRICT,
                requested_by TEXT NOT NULL REFERENCES users(id) ON DELETE RESTRICT,
                reason TEXT NOT NULL CHECK (length(trim(reason)) BETWEEN 1 AND 1000),
                optional_note TEXT,
                requested_at INTEGER NOT NULL,
                previous_status TEXT NOT NULL CHECK (previous_status IN ('CLASSIFIED', 'RESOLVED')),
                status TEXT NOT NULL CHECK (status IN
                    ('PENDING', 'NEEDS_INFO', 'APPROVED', 'REJECTED')),
                decided_by TEXT REFERENCES users(id) ON DELETE RESTRICT,
                decided_at INTEGER,
                decision_reason TEXT
            )
        """)
        connection.execute("""
            CREATE UNIQUE INDEX one_open_reopen_request ON reopen_requests(comment_id)
            WHERE status IN ('PENDING', 'NEEDS_INFO')
        """)
        connection.execute("CREATE INDEX reopen_request_status ON reopen_requests(status, requested_at)")
        connection.execute("""
            CREATE TABLE reopen_updates (
                seq INTEGER PRIMARY KEY AUTOINCREMENT,
                id TEXT NOT NULL UNIQUE,
                request_id TEXT NOT NULL REFERENCES reopen_requests(id) ON DELETE RESTRICT,
                actor_id TEXT NOT NULL REFERENCES users(id) ON DELETE RESTRICT,
                kind TEXT NOT NULL CHECK (kind IN ('INFO_REQUESTED', 'INFO_PROVIDED')),
                note TEXT NOT NULL CHECK (length(trim(note)) BETWEEN 1 AND 1000),
                created_at INTEGER NOT NULL
            )
        """)
        connection.execute("CREATE INDEX reopen_updates_request ON reopen_updates(request_id, seq)")
        connection.execute("""
            CREATE TABLE supervisor_actions (
                id TEXT PRIMARY KEY NOT NULL,
                comment_id TEXT NOT NULL REFERENCES comments(id) ON DELETE RESTRICT,
                actor_id TEXT NOT NULL REFERENCES users(id) ON DELETE RESTRICT,
                action_type TEXT NOT NULL CHECK (action_type IN ('RESOLVE', 'REASSIGN')),
                reason TEXT NOT NULL CHECK (length(trim(reason)) BETWEEN 1 AND 1000),
                target_user_id TEXT REFERENCES users(id) ON DELETE RESTRICT,
                recommend_removal INTEGER CHECK (recommend_removal IN (0, 1)),
                created_at INTEGER NOT NULL
            )
        """)

    @staticmethod
    def _migrate_audit_events(connection: sqlite3.Connection) -> None:
        # SQLite cannot extend an existing CHECK constraint in place. Preserve IDs
        # so historic ordering and review references survive the table replacement.
        connection.execute("""
            CREATE TABLE audit_events_v3 (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                comment_id TEXT NOT NULL REFERENCES comments(id) ON DELETE RESTRICT,
                actor_id TEXT,
                actor_display_name TEXT,
                event_type TEXT NOT NULL CHECK (event_type IN
                    ('assigned', 'claim_expired', 'content_revealed',
                     'classified', 'escalated', 'reopen_requested',
                     'reopen_approved', 'reopen_rejected', 'reopen_info_requested',
                     'reopen_info_provided', 'reassigned', 'resolved')),
                created_at INTEGER NOT NULL,
                review_id TEXT REFERENCES reviews(id),
                reopen_request_id TEXT REFERENCES reopen_requests(id),
                reopen_update_id TEXT REFERENCES reopen_updates(id),
                supervisor_action_id TEXT REFERENCES supervisor_actions(id)
            )
        """)
        connection.execute("""
            INSERT INTO audit_events_v3
                (id, comment_id, actor_id, actor_display_name, event_type, created_at, review_id)
            SELECT id, comment_id, actor_id, actor_display_name, event_type, created_at, review_id
            FROM audit_events
        """)
        connection.execute("DROP TABLE audit_events")
        connection.execute("ALTER TABLE audit_events_v3 RENAME TO audit_events")
        connection.execute("CREATE INDEX audit_comment ON audit_events(comment_id, id)")

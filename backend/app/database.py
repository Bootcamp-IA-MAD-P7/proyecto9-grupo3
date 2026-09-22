"""Versioned storage for portal users and comments.

SQLite remains the local-development and test backend.  Production can use a
Postgres URL (including a pooled Neon URL), which is safe to share across
Vercel Function instances.
"""

import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Iterator


SCHEMA_VERSION = 4


class _PostgresConnection:
    """Small compatibility layer for the repository's DB-API style queries."""

    def __init__(self, connection: Any):
        self._connection = connection

    @staticmethod
    def _sql(statement: str) -> str:
        return statement.replace("?", "%s")

    def execute(self, statement: str, parameters: tuple[Any, ...] = ()):
        if statement.strip().upper() == "BEGIN IMMEDIATE":
            statement = "BEGIN"
        return self._connection.execute(self._sql(statement), parameters)

    def executemany(self, statement: str, parameters: list[tuple[Any, ...]]):
        return self._connection.executemany(self._sql(statement), parameters)


class Database:
    def __init__(self, target: Path | str):
        value = str(target)
        self.url = value if value.startswith(("postgres://", "postgresql://")) else None
        self.path = None if self.url else Path(target).resolve()

    @property
    def is_postgres(self) -> bool:
        return self.url is not None

    @contextmanager
    def connect(self) -> Iterator[Any]:
        if self.url:
            try:
                import psycopg
                from psycopg.rows import dict_row
            except ImportError as error:  # pragma: no cover - deployment dependency guard
                raise RuntimeError("Postgres support requires psycopg") from error
            with psycopg.connect(
                self.url,
                row_factory=dict_row,
                connect_timeout=10,
                prepare_threshold=None,
            ) as connection:
                yield _PostgresConnection(connection)
            return

        assert self.path is not None
        connection = sqlite3.connect(self.path, timeout=5)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys=ON")
        try:
            with connection:
                yield connection
        finally:
            connection.close()

    def initialize(self) -> None:
        if self.is_postgres:
            self._initialize_postgres()
            return

        assert self.path is not None
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            version = connection.execute("PRAGMA user_version").fetchone()[0]
            if version not in range(SCHEMA_VERSION + 1):
                raise RuntimeError("Unsupported database schema version")
            if version == SCHEMA_VERSION:
                return
            if version == 0:
                self._create_persistence_schema(connection)
            if version < 2:
                self._create_auth_schema(connection)
            self._add_scoring_schema(connection)
            if version < 4:
                self._add_review_schema(connection)
            connection.execute(f"PRAGMA user_version={SCHEMA_VERSION}")

    def _initialize_postgres(self) -> None:
        with self.connect() as connection:
            # Serialize cold-start schema checks from concurrent Function instances.
            connection.execute("SELECT pg_advisory_xact_lock(78624319)")
            connection.execute("""
                CREATE TABLE IF NOT EXISTS moderation_schema (
                    singleton BOOLEAN PRIMARY KEY DEFAULT TRUE CHECK (singleton),
                    version INTEGER NOT NULL
                )
            """)
            version_row = connection.execute(
                "SELECT version FROM moderation_schema WHERE singleton=TRUE"
            ).fetchone()
            if version_row is not None and version_row["version"] != SCHEMA_VERSION:
                raise RuntimeError("Unsupported database schema version")
            self._create_postgres_schema(connection)
            connection.execute("""
                INSERT INTO moderation_schema(singleton, version) VALUES (TRUE, ?)
                ON CONFLICT(singleton) DO NOTHING
            """, (SCHEMA_VERSION,))

    def _create_postgres_schema(self, connection: Any) -> None:
        connection.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id TEXT PRIMARY KEY,
                username TEXT NOT NULL UNIQUE,
                display_name TEXT NOT NULL,
                password_hash TEXT NOT NULL,
                role TEXT NOT NULL CHECK (role IN ('MODERATOR', 'SUPERVISOR')),
                is_active BOOLEAN NOT NULL DEFAULT TRUE,
                created_at BIGINT NOT NULL
            )
        """)
        connection.execute("""
            CREATE TABLE IF NOT EXISTS comments (
                sequence BIGSERIAL PRIMARY KEY,
                comment_id TEXT NOT NULL UNIQUE,
                video_id TEXT NOT NULL,
                text TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'PENDING'
                    CHECK (status IN ('PENDING', 'IN_REVIEW', 'REVIEWED',
                                     'CLASSIFIED', 'ESCALATED', 'RESOLVED',
                                     'REOPEN_REQUESTED', 'REOPENED')),
                assignee_id TEXT REFERENCES users(id) ON DELETE RESTRICT,
                risk_score DOUBLE PRECISION CHECK (risk_score BETWEEN 0 AND 1),
                uncertainty DOUBLE PRECISION CHECK (uncertainty BETWEEN 0 AND 1),
                model_version TEXT,
                score_source TEXT CHECK (score_source IN ('SIMULATED', 'MODEL')),
                review_decision TEXT
                    CHECK (review_decision IN ('CONFIRMED_TOXIC', 'NOT_TOXIC', 'NEEDS_REVIEW')),
                reviewed_by TEXT REFERENCES users(id) ON DELETE RESTRICT,
                reviewed_at TEXT,
                review_notes TEXT
            )
        """)
        connection.execute("""
            CREATE TABLE IF NOT EXISTS sessions (
                token_hash TEXT PRIMARY KEY CHECK (length(token_hash) = 64),
                user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                created_at BIGINT NOT NULL,
                expires_at BIGINT NOT NULL CHECK (expires_at > created_at)
            )
        """)
        connection.execute("""
            CREATE TABLE IF NOT EXISTS login_attempts (
                username TEXT PRIMARY KEY,
                attempts INTEGER NOT NULL CHECK (attempts > 0),
                window_started_at BIGINT NOT NULL
            )
        """)
        connection.execute("CREATE INDEX IF NOT EXISTS sessions_expiry ON sessions(expires_at)")
        connection.execute("CREATE INDEX IF NOT EXISTS sessions_user ON sessions(user_id)")
        connection.execute("CREATE INDEX IF NOT EXISTS attempts_window ON login_attempts(window_started_at)")
        connection.execute("CREATE INDEX IF NOT EXISTS comments_status_order ON comments(status, sequence)")
        connection.execute("""
            CREATE INDEX IF NOT EXISTS comments_queue
            ON comments(status, risk_score DESC, sequence ASC)
        """)

    def _add_review_schema(self, connection: sqlite3.Connection) -> None:
        """Add review traceability and a status constraint that includes REVIEWED."""
        connection.execute("ALTER TABLE comments RENAME TO comments_legacy")
        connection.execute("""
            CREATE TABLE comments (
                sequence INTEGER PRIMARY KEY AUTOINCREMENT,
                comment_id TEXT NOT NULL UNIQUE,
                video_id TEXT NOT NULL,
                text TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'PENDING'
                    CHECK (status IN ('PENDING', 'IN_REVIEW', 'REVIEWED',
                                     'CLASSIFIED', 'ESCALATED', 'RESOLVED',
                                     'REOPEN_REQUESTED', 'REOPENED')),
                assignee_id TEXT REFERENCES users(id) ON DELETE RESTRICT,
                risk_score REAL CHECK (risk_score BETWEEN 0 AND 1),
                uncertainty REAL CHECK (uncertainty BETWEEN 0 AND 1),
                model_version TEXT,
                score_source TEXT CHECK (score_source IN ('SIMULATED', 'MODEL')),
                review_decision TEXT CHECK (review_decision IN ('CONFIRMED_TOXIC', 'NOT_TOXIC', 'NEEDS_REVIEW')),
                reviewed_by TEXT REFERENCES users(id) ON DELETE RESTRICT,
                reviewed_at TEXT,
                review_notes TEXT
            )
        """)
        connection.execute("""
            INSERT INTO comments(sequence, comment_id, video_id, text, status, assignee_id,
                risk_score, uncertainty, model_version, score_source)
            SELECT sequence, comment_id, video_id, text, status, assignee_id,
                risk_score, uncertainty, model_version, score_source
            FROM comments_legacy
        """)
        connection.execute("DROP TABLE comments_legacy")
        connection.execute("CREATE INDEX comments_status_order ON comments(status, sequence)")
        connection.execute("CREATE INDEX comments_queue ON comments(status, risk_score DESC, sequence ASC)")

    def _create_auth_schema(self, connection: sqlite3.Connection) -> None:
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

    def _add_scoring_schema(self, connection: sqlite3.Connection) -> None:
        from app.comments.scoring import SimulatedScorer

        connection.execute("ALTER TABLE comments ADD COLUMN risk_score REAL CHECK (risk_score BETWEEN 0 AND 1)")
        connection.execute("ALTER TABLE comments ADD COLUMN uncertainty REAL CHECK (uncertainty BETWEEN 0 AND 1)")
        connection.execute("ALTER TABLE comments ADD COLUMN model_version TEXT")
        connection.execute("ALTER TABLE comments ADD COLUMN score_source TEXT CHECK (score_source IN ('SIMULATED', 'MODEL'))")
        scorer = SimulatedScorer()
        for row in connection.execute("SELECT sequence, text FROM comments"):
            score = scorer.score_comment(row["text"])
            connection.execute("""
                UPDATE comments SET risk_score=?, uncertainty=?, model_version=?, score_source=?
                WHERE sequence=?
            """, (score.risk_score, score.uncertainty, score.model_version,
                  score.score_source, row["sequence"]))
        connection.execute("CREATE INDEX comments_queue ON comments(status, risk_score DESC, sequence ASC)")

    def _create_persistence_schema(self, connection: sqlite3.Connection) -> None:
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
            CREATE TABLE comments (
                sequence INTEGER PRIMARY KEY AUTOINCREMENT,
                comment_id TEXT NOT NULL UNIQUE,
                video_id TEXT NOT NULL,
                text TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'PENDING'
                    CHECK (status IN ('PENDING', 'IN_REVIEW', 'CLASSIFIED',
                                     'ESCALATED', 'RESOLVED', 'REOPEN_REQUESTED', 'REOPENED')),
                assignee_id TEXT REFERENCES users(id) ON DELETE RESTRICT
            )
        """)
        connection.execute("CREATE INDEX comments_status_order ON comments(status, sequence)")

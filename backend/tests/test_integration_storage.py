"""Migration and queue contracts shared by all backend workflows."""

import sqlite3

from app.database import Database


def test_fresh_database_has_integrated_schema(tmp_path):
    database = Database(tmp_path / "integrated.db")
    database.initialize()
    with database.connect() as connection:
        assert connection.execute("PRAGMA user_version").fetchone()[0] == 5
        tables = {row[0] for row in connection.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        )}
        assert {"users", "comments", "assignments", "reviews", "audit_events",
                "reopen_requests", "supervisor_actions"} <= tables
        columns = Database._columns(connection, "comments")
        assert {"id", "source_order", "uncertainty", "score_source"} <= columns
    database.initialize()


def test_unknown_version_three_shape_is_unchanged(tmp_path):
    path = tmp_path / "unknown.db"
    with sqlite3.connect(path) as connection:
        connection.execute("CREATE TABLE comments (unexpected TEXT)")
        connection.execute("PRAGMA user_version=3")
    try:
        Database(path).initialize()
    except RuntimeError:
        pass
    else:
        raise AssertionError("Unknown schema accepted")
    with sqlite3.connect(path) as connection:
        assert connection.execute("PRAGMA user_version").fetchone()[0] == 3
        assert connection.execute("PRAGMA table_info(comments)").fetchone()[1] == "unexpected"


def test_dev_queue_version_three_preserves_scores_and_order(tmp_path):
    path = tmp_path / "queue-v3.db"
    database = Database(path)
    with database.connect() as connection:
        database._create_auth_schema(connection)
        connection.execute("""CREATE TABLE comments (
            sequence INTEGER PRIMARY KEY AUTOINCREMENT,
            comment_id TEXT NOT NULL UNIQUE, video_id TEXT NOT NULL, text TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'PENDING',
            assignee_id TEXT REFERENCES users(id), risk_score REAL, uncertainty REAL,
            model_version TEXT, score_source TEXT)""")
        connection.execute("CREATE INDEX comments_queue ON comments(status, risk_score DESC, sequence ASC)")
        connection.execute("""INSERT INTO comments
            (comment_id, video_id, text, risk_score, uncertainty, model_version, score_source)
            VALUES ('legacy-1', 'video-1', 'synthetic text', .7, .6, 'model-v1', 'MODEL')""")
        connection.execute("PRAGMA user_version=3")
    database.initialize()
    with database.connect() as connection:
        assert connection.execute("PRAGMA user_version").fetchone()[0] == 5
        row = connection.execute("SELECT * FROM comments WHERE id='legacy-1'").fetchone()
        assert (row["source_order"], row["risk_score"], row["uncertainty"],
                row["score_source"], row["text"]) == (1, .7, .6, "MODEL", "synthetic text")
        assert connection.execute("PRAGMA foreign_key_check").fetchall() == []


def test_dev_queue_migration_keeps_active_assignee(tmp_path):
    import time

    path = tmp_path / "assigned-v3.db"
    database = Database(path)
    with database.connect() as connection:
        database._create_auth_schema(connection)
        connection.execute("""INSERT INTO users
            (id, username, display_name, password_hash, role, created_at)
            VALUES ('u-1', 'moderator', 'Moderator', 'synthetic-hash', 'MODERATOR', 1)""")
        connection.execute("""CREATE TABLE comments (
            sequence INTEGER PRIMARY KEY AUTOINCREMENT,
            comment_id TEXT NOT NULL UNIQUE, video_id TEXT NOT NULL, text TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'PENDING',
            assignee_id TEXT REFERENCES users(id), risk_score REAL, uncertainty REAL,
            model_version TEXT, score_source TEXT)""")
        connection.execute("CREATE INDEX comments_queue ON comments(status, risk_score DESC, sequence ASC)")
        connection.execute("""INSERT INTO comments
            (comment_id, video_id, text, status, assignee_id,
             risk_score, uncertainty, model_version, score_source)
            VALUES ('assigned-1', 'video-1', 'synthetic text', 'IN_REVIEW', 'u-1',
                    .7, .6, 'model-v1', 'MODEL')""")
        connection.execute("PRAGMA user_version=3")
    database.initialize()
    with database.connect() as connection:
        assignment = connection.execute("""SELECT reviewer_id, expires_at
            FROM assignments WHERE comment_id='assigned-1' AND closed_at IS NULL""").fetchone()
        assert assignment["reviewer_id"] == "u-1"
        assert assignment["expires_at"] > int(time.time())

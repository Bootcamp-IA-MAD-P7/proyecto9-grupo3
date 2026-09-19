"""Step 2 persistence contracts against temporary SQLite files."""

import sqlite3

import pytest

from app.database import Database


def test_first_initialization_creates_users_and_comments_and_is_idempotent(tmp_path):
    database = Database(tmp_path / "nested" / "moderation.db")
    database.initialize()
    with database.connect() as connection:
        assert connection.execute("PRAGMA user_version").fetchone()[0] == 5
        assert {row[0] for row in connection.execute("SELECT name FROM sqlite_master WHERE type='table'")} >= {
            "users", "comments"
        }
        connection.execute("""
            INSERT INTO users(id,username,display_name,password_hash,role,created_at)
            VALUES ('u1','moderator','Demo Moderator','$argon2id$synthetic','MODERATOR',1)
        """)
        connection.execute("""
            INSERT INTO comments(id,video_id,text,risk_score,model_version,source_order)
            VALUES ('c1','v1','Synthetic comment',0.5,'synthetic-v1',1)
        """)
    database.initialize()
    with database.connect() as connection:
        assert connection.execute("SELECT count(*) FROM users").fetchone()[0] == 1
        assert connection.execute("SELECT count(*) FROM comments").fetchone()[0] == 1
        row = connection.execute("SELECT source_order, status FROM comments").fetchone()
        assert tuple(row) == (1, "PENDING")


def test_foreign_keys_and_roles_reject_invalid_data(tmp_path):
    database = Database(tmp_path / "constraints.db")
    database.initialize()
    with pytest.raises(sqlite3.IntegrityError), database.connect() as connection:
        connection.execute("""INSERT INTO assignments
            (comment_id,reviewer_id,claimed_at,expires_at)
            VALUES ('missing-comment','missing-user',1,2)""")
    with pytest.raises(sqlite3.IntegrityError), database.connect() as connection:
        connection.execute("""
            INSERT INTO users(id,username,display_name,password_hash,role,created_at)
            VALUES ('u1','moderator','Demo Moderator','hash','ADMIN',1)
        """)


def test_failed_batch_rolls_back_all_comments(tmp_path):
    database = Database(tmp_path / "rollback.db")
    database.initialize()
    with pytest.raises(sqlite3.IntegrityError), database.connect() as connection:
        connection.executemany("""
            INSERT INTO comments(id,video_id,text,risk_score,model_version,source_order)
            VALUES (?,?,?,?,?,?)
        """, [("c1", "v1", "Synthetic one", 0.5, "synthetic-v1", 1),
               ("c1", "v1", "Synthetic two", 0.5, "synthetic-v1", 2)])
    with database.connect() as connection:
        assert connection.execute("SELECT count(*) FROM comments").fetchone()[0] == 0

"""Step 2 persistence contracts against temporary SQLite files."""

import sqlite3

import pytest

from app.database import Database


def test_first_initialization_creates_users_and_comments_and_is_idempotent(tmp_path):
    database = Database(tmp_path / "nested" / "moderation.db")
    database.initialize()
    with database.connect() as connection:
        assert connection.execute("PRAGMA user_version").fetchone()[0] == 4
        assert {row[0] for row in connection.execute("SELECT name FROM sqlite_master WHERE type='table'")} >= {
            "users", "comments"
        }
        connection.execute("""
            INSERT INTO users(id,username,display_name,password_hash,role,created_at)
            VALUES ('u1','moderator','Demo Moderator','$argon2id$synthetic','MODERATOR',1)
        """)
        connection.execute("""
            INSERT INTO comments(comment_id,video_id,text,assignee_id)
            VALUES ('c1','v1','Synthetic comment','u1')
        """)
    database.initialize()
    with database.connect() as connection:
        assert connection.execute("SELECT count(*) FROM users").fetchone()[0] == 1
        assert connection.execute("SELECT count(*) FROM comments").fetchone()[0] == 1
        row = connection.execute("SELECT sequence, status, assignee_id FROM comments").fetchone()
        assert tuple(row) == (1, "PENDING", "u1")


def test_foreign_keys_and_roles_reject_invalid_data(tmp_path):
    database = Database(tmp_path / "constraints.db")
    database.initialize()
    with pytest.raises(sqlite3.IntegrityError), database.connect() as connection:
        connection.execute("""
            INSERT INTO comments(comment_id,video_id,text,assignee_id)
            VALUES ('c1','v1','Synthetic comment','missing')
        """)
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
            INSERT INTO comments(comment_id,video_id,text) VALUES (?,?,?)
        """, [("c1", "v1", "Synthetic one"), ("c1", "v1", "Synthetic two")])
    with database.connect() as connection:
        assert connection.execute("SELECT count(*) FROM comments").fetchone()[0] == 0

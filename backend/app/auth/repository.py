"""Parameterized persistence operations; no HTTP or password verification here."""

import sqlite3

from app.auth.models import Role, User
from app.database import Database


def _user(row: sqlite3.Row | None) -> User | None:
    if row is None:
        return None
    return User(
        id=row["id"], username=row["username"], display_name=row["display_name"],
        password_hash=row["password_hash"], role=Role(row["role"]),
        is_active=bool(row["is_active"]),
    )


class AuthRepository:
    def __init__(self, database: Database):
        self.database = database

    def find_user(self, username: str) -> User | None:
        with self.database.connect() as connection:
            return _user(connection.execute(
                "SELECT * FROM users WHERE username=?", (username,)
            ).fetchone())

    def create_session(self, digest: str, user_id: str, now: int, expires: int) -> None:
        with self.database.connect() as connection:
            connection.execute("DELETE FROM sessions WHERE expires_at<=?", (now,))
            connection.execute(
                "INSERT INTO sessions(token_hash, user_id, created_at, expires_at) VALUES (?, ?, ?, ?)",
                (digest, user_id, now, expires),
            )

    def session_user(self, digest: str, now: int) -> User | None:
        with self.database.connect() as connection:
            return _user(connection.execute("""
                SELECT users.* FROM sessions JOIN users ON users.id=sessions.user_id
                WHERE sessions.token_hash=? AND sessions.expires_at>? AND users.is_active=1
            """, (digest, now)).fetchone())

    def revoke_session(self, digest: str) -> None:
        with self.database.connect() as connection:
            connection.execute("DELETE FROM sessions WHERE token_hash=?", (digest,))

    def record_attempt(self, username: str, now: int, limit: int, window: int) -> int | None:
        """Reserve one attempt atomically; return seconds to wait when exhausted."""
        with self.database.connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            connection.execute("DELETE FROM login_attempts WHERE window_started_at<=?", (now - window,))
            row = connection.execute(
                "SELECT * FROM login_attempts WHERE username=?", (username,)
            ).fetchone()
            if row is not None and row["attempts"] >= limit:
                return max(1, row["window_started_at"] + window - now)
            connection.execute("""
                INSERT INTO login_attempts(username, attempts, window_started_at) VALUES (?, 1, ?)
                ON CONFLICT(username) DO UPDATE SET attempts=attempts+1
            """, (username, now))
        return None

    def clear_attempts(self, username: str) -> None:
        with self.database.connect() as connection:
            connection.execute("DELETE FROM login_attempts WHERE username=?", (username,))

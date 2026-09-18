"""Versioned SQLite storage for portal users and comments."""

import sqlite3
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
            if version not in (0, 1):
                raise RuntimeError("Unsupported database schema version")
            if version == 1:
                return
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
            connection.execute("PRAGMA user_version=1")

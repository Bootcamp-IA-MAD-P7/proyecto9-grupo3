"""Provision demo users locally, with no committed default passwords."""

import getpass
import os
import time
import uuid

from pwdlib import PasswordHash

from app.config import Settings
from app.database import Database


def seed_demo_users(database: Database, moderator_password: str, supervisor_password: str) -> None:
    for password in (moderator_password, supervisor_password):
        if not 12 <= len(password) <= 1024:
            raise ValueError("Demo passwords must contain 12 to 1024 characters")
    database.initialize()
    hasher = PasswordHash.recommended()
    # Hash before acquiring the write lock. Repeated calls preserve existing users.
    records = [
        (str(uuid.uuid4()), "moderator", "Demo Moderator", hasher.hash(moderator_password), "MODERATOR", int(time.time())),
        (str(uuid.uuid4()), "supervisor", "Demo Supervisor", hasher.hash(supervisor_password), "SUPERVISOR", int(time.time())),
    ]
    with database.connect() as connection:
        connection.executemany("""
            INSERT INTO users(id, username, display_name, password_hash, role, created_at)
            VALUES (?, ?, ?, ?, ?, ?) ON CONFLICT(username) DO NOTHING
        """, records)


def main() -> None:
    settings = Settings()
    moderator_password = os.environ.get("MODERATION_DEMO_MODERATOR_PASSWORD")
    supervisor_password = os.environ.get("MODERATION_DEMO_SUPERVISOR_PASSWORD")
    if moderator_password is None:
        moderator_password = getpass.getpass("Password for moderator (12+ characters): ")
    if supervisor_password is None:
        supervisor_password = getpass.getpass("Password for supervisor (12+ characters): ")
    try:
        seed_demo_users(Database(settings.database_path), moderator_password, supervisor_password)
    except ValueError as error:
        raise SystemExit(str(error)) from None
    print("Demo users ready: moderator, supervisor. Existing credentials were preserved.")


if __name__ == "__main__":
    main()

"""Reset a private reviewer password explicitly from a terminal."""

import argparse
import getpass

from pwdlib import PasswordHash

from app.config import Settings
from app.database import Database


def reset_password(database: Database, username: str, password: str) -> None:
    if not 12 <= len(password) <= 1024:
        raise ValueError("Passwords must contain 12 to 1024 characters")
    database.initialize()
    password_hash = PasswordHash.recommended().hash(password)
    with database.connect() as connection:
        updated = connection.execute(
            "UPDATE users SET password_hash=? WHERE username=? AND role IN ('MODERATOR', 'SUPERVISOR')",
            (password_hash, username),
        ).rowcount
        if updated != 1:
            raise ValueError("Private reviewer account was not found")
        connection.execute("DELETE FROM sessions WHERE user_id=(SELECT id FROM users WHERE username=?)", (username,))


def main() -> None:
    parser = argparse.ArgumentParser(description="Reset a moderator or supervisor password.")
    parser.add_argument("username", choices=("moderator", "supervisor"))
    args = parser.parse_args()
    password = getpass.getpass(f"New password for {args.username} (12+ characters): ")
    confirmation = getpass.getpass("Repeat new password: ")
    if password != confirmation:
        raise SystemExit("Passwords do not match")
    try:
        reset_password(Database(Settings().database_path), args.username, password)
    except ValueError as error:
        raise SystemExit(str(error)) from None
    print(f"Password hash updated for {args.username}; existing sessions were revoked.")


if __name__ == "__main__":
    main()

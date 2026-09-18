"""Use a password KDF for passwords and a digest for high-entropy session tokens."""

import hashlib
import re
import secrets

from pwdlib import PasswordHash
from pwdlib.exceptions import UnknownHashError


class Passwords:
    def __init__(self):
        self.hasher = PasswordHash.recommended()
        self.dummy_hash = self.hasher.hash(secrets.token_urlsafe(32))

    def hash(self, password: str) -> str:
        return self.hasher.hash(password)

    def verify(self, password: str, stored_hash: str | None) -> bool:
        try:
            return self.hasher.verify(password, stored_hash or self.dummy_hash)
        except UnknownHashError:
            return False


def new_token() -> str:
    return secrets.token_urlsafe(32)


def token_digest(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def valid_token_shape(token: str) -> bool:
    return re.fullmatch(r"[A-Za-z0-9_-]{43}", token) is not None

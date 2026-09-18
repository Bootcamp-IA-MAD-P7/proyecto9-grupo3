"""Authentication rules, independent of FastAPI's request/response objects."""

import time

from app.auth.models import User
from app.auth.repository import AuthRepository
from app.auth.security import Passwords, new_token, token_digest, valid_token_shape
from app.config import Settings


class InvalidCredentials(Exception):
    pass


class TooManyAttempts(Exception):
    def __init__(self, retry_after: int):
        self.retry_after = retry_after
        super().__init__("Login temporarily limited")


class AuthService:
    def __init__(self, repository: AuthRepository, settings: Settings):
        self.repository = repository
        self.settings = settings
        self.passwords = Passwords()

    def login(self, username: str, password: str) -> tuple[str, User]:
        username = username.strip().lower()
        now = int(time.time())
        wait = self.repository.record_attempt(
            username, now, self.settings.login_max_attempts, self.settings.login_window_seconds
        )
        if wait is not None:
            raise TooManyAttempts(wait)
        user = self.repository.find_user(username)
        verified = self.passwords.verify(password, user.password_hash if user else None)
        if not verified or user is None or not user.is_active:
            raise InvalidCredentials()
        token = new_token()
        now = int(time.time())
        self.repository.create_session(token_digest(token), user.id, now, now + self.settings.session_ttl_seconds)
        self.repository.clear_attempts(username)
        return token, user

    def authenticate(self, token: str) -> User | None:
        if not valid_token_shape(token):
            return None
        return self.repository.session_user(token_digest(token), int(time.time()))

    def logout(self, token: str) -> None:
        self.repository.revoke_session(token_digest(token))

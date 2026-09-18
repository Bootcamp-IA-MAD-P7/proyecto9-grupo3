"""Reusable guards for routes: authenticate first, authorize second."""

from collections.abc import Callable
from typing import Annotated

from fastapi import Depends, HTTPException, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.auth.models import Role, User
from app.auth.service import AuthService

bearer = HTTPBearer(auto_error=False)


def unauthorized() -> HTTPException:
    return HTTPException(401, "Invalid credentials or session", headers={"WWW-Authenticate": "Bearer"})


def get_auth_service(request: Request) -> AuthService:
    return request.app.state.auth_service


def get_bearer_token(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer)],
) -> str:
    if credentials is None:
        raise unauthorized()
    return credentials.credentials


def get_current_user(
    token: Annotated[str, Depends(get_bearer_token)],
    service: Annotated[AuthService, Depends(get_auth_service)],
) -> User:
    user = service.authenticate(token)
    if user is None:
        raise unauthorized()
    return user


def require_roles(*roles: Role) -> Callable:
    if not roles:
        raise ValueError("At least one allowed role is required")

    def guard(user: Annotated[User, Depends(get_current_user)]) -> User:
        if user.role not in roles:
            raise HTTPException(403, "Insufficient permissions")
        return user

    return guard

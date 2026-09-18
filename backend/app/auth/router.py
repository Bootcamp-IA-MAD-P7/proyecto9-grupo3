"""Map HTTP contracts to the authentication service."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Response

from app.auth.dependencies import get_auth_service, get_bearer_token, get_current_user, unauthorized
from app.auth.models import User
from app.auth.schemas import LoginRequest, LoginResponse, PublicUser
from app.auth.service import AuthService, InvalidCredentials, TooManyAttempts

router = APIRouter(prefix="/auth", tags=["authentication"])
Auth = Annotated[AuthService, Depends(get_auth_service)]
CurrentUser = Annotated[User, Depends(get_current_user)]


@router.post("/login", response_model=LoginResponse, responses={401: {"description": "Invalid credentials"}, 429: {"description": "Too many attempts"}})
def login(body: LoginRequest, service: Auth) -> LoginResponse:
    try:
        token, user = service.login(body.username, body.password.get_secret_value())
    except InvalidCredentials:
        raise unauthorized() from None
    except TooManyAttempts as error:
        raise HTTPException(429, "Too many login attempts", headers={"Retry-After": str(error.retry_after)}) from None
    return LoginResponse(
        access_token=token,
        expires_in=service.settings.session_ttl_seconds,
        user=PublicUser.model_validate(user),
    )


@router.get("/me", response_model=PublicUser, responses={401: {"description": "Invalid session"}})
def me(user: CurrentUser) -> PublicUser:
    return PublicUser.model_validate(user)


@router.post("/logout", status_code=204, responses={401: {"description": "Invalid session"}})
def logout(user: CurrentUser, token: Annotated[str, Depends(get_bearer_token)], service: Auth) -> Response:
    service.logout(token)
    return Response(status_code=204)

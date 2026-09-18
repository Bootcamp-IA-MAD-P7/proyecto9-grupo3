"""The API deliberately exposes fewer fields than its stored user records."""

from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, SecretStr, StringConstraints, field_validator

from app.auth.models import Role


class LoginRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    username: Annotated[str, StringConstraints(strip_whitespace=True, to_lower=True, min_length=1, max_length=64)]
    password: SecretStr = Field(min_length=1, max_length=1024)

    @field_validator("password")
    @classmethod
    def password_is_valid_utf8(cls, password: SecretStr) -> SecretStr:
        try:
            password.get_secret_value().encode("utf-8")
        except UnicodeEncodeError:
            raise ValueError("Password must be valid UTF-8") from None
        return password


class PublicUser(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    username: str
    display_name: str
    role: Role


class LoginResponse(BaseModel):
    access_token: str
    token_type: Literal["bearer"] = "bearer"
    expires_in: int
    user: PublicUser

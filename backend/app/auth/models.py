"""Internal user representation; never serialize this record directly."""

from dataclasses import dataclass, field
from enum import StrEnum


class Role(StrEnum):
    MODERATOR = "MODERATOR"
    SUPERVISOR = "SUPERVISOR"


@dataclass(frozen=True)
class User:
    id: str
    username: str
    display_name: str
    role: Role
    is_active: bool
    password_hash: str = field(repr=False)

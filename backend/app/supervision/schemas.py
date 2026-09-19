"""Public supervision requests and responses; no stored comment text."""

from enum import StrEnum
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class StrictBody(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class ReasonBody(StrictBody):
    reason: str = Field(min_length=1, max_length=1000)


class ReopenRequestBody(ReasonBody):
    optional_note: str | None = Field(default=None, max_length=1000)


class InformationBody(StrictBody):
    note: str = Field(min_length=1, max_length=1000)


class ReassignBody(ReasonBody):
    reviewer_id: str = Field(min_length=1, max_length=100)


class ResolveBody(ReasonBody):
    recommend_removal: bool = False


class RequestStatus(StrEnum):
    PENDING = "PENDING"
    NEEDS_INFO = "NEEDS_INFO"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"


class ReopenUpdateResponse(BaseModel):
    id: str
    actor_id: str
    kind: Literal["INFO_REQUESTED", "INFO_PROVIDED"]
    note: str
    created_at: int


class ReopenResponse(BaseModel):
    request_id: str
    comment_id: str
    requested_by: str
    reason: str
    optional_note: str | None
    requested_at: int
    previous_status: Literal["CLASSIFIED", "RESOLVED"]
    status: RequestStatus
    decided_by: str | None
    decided_at: int | None
    decision_reason: str | None
    updates: list[ReopenUpdateResponse]


class ResolveResponse(BaseModel):
    action_id: str
    comment_id: str
    status: Literal["RESOLVED"]
    reason: str
    recommend_removal: bool


class ReassignResponse(BaseModel):
    action_id: str
    comment_id: str
    status: Literal["IN_REVIEW"]
    reviewer_id: str
    claim_expires_at: int

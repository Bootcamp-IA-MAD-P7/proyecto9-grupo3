"""Public comment contracts; queue and history never carry stored text."""

from enum import StrEnum
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


class CommentStatus(StrEnum):
    PENDING = "PENDING"
    IN_REVIEW = "IN_REVIEW"
    CLASSIFIED = "CLASSIFIED"
    ESCALATED = "ESCALATED"
    RESOLVED = "RESOLVED"
    REOPEN_REQUESTED = "REOPEN_REQUESTED"
    REOPENED = "REOPENED"


class ReviewResult(StrEnum):
    NO_ESCALATION = "NO_ESCALATION"
    ESCALATE_TO_SUPERVISOR = "ESCALATE_TO_SUPERVISOR"
    INSUFFICIENT_CONTEXT = "INSUFFICIENT_CONTEXT"
    TRANSFER_REQUESTED = "TRANSFER_REQUESTED"


class CommentSummary(BaseModel):
    comment_id: str
    video_id: str
    risk_score: float
    model_version: str
    status: CommentStatus


class ImportItem(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    comment_id: str = Field(min_length=1, max_length=128)
    video_id: str = Field(min_length=1, max_length=128)
    text: str = Field(min_length=1, max_length=5000)


class ImportRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    items: list[ImportItem] = Field(min_length=1, max_length=1000)

    @model_validator(mode="after")
    def unique_ids(self):
        ids = [item.comment_id for item in self.items]
        if len(ids) != len(set(ids)):
            raise ValueError("Duplicate comment IDs in batch")
        return self


class ImportResponse(BaseModel):
    imported: int


class QueueItem(CommentSummary):
    uncertainty: float
    score_source: Literal["SIMULATED", "MODEL"]


class QueuePage(BaseModel):
    items: list[QueueItem]
    page: int
    page_size: int
    total: int
    has_next: bool


class ClaimResponse(BaseModel):
    comment_id: str
    status: Literal["IN_REVIEW"]
    claim_expires_at: int


class ContentResponse(BaseModel):
    comment_id: str
    text: str


class ReviewRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    result: ReviewResult
    reason: str = Field(min_length=1, max_length=1000)


class ReviewResponse(BaseModel):
    review_id: str
    comment_id: str
    reviewer_id: str
    reviewer_display_name: str
    result: ReviewResult
    reason: str
    created_at: int
    model_score: float
    model_version: str
    status: CommentStatus


class HistoryEvent(BaseModel):
    event_type: str
    actor_id: str | None
    actor_display_name: str | None
    created_at: int
    result: ReviewResult | None = None
    reason: str | None = None
    model_score: float | None = None
    model_version: str | None = None
    target_reviewer_id: str | None = None
    recommend_removal: bool | None = None


class HistoryResponse(BaseModel):
    comment_id: str
    status: CommentStatus
    events: list[HistoryEvent]

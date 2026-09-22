"""Validated public contracts. Queue entries intentionally omit comment text."""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


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
        if len(set(ids)) != len(ids):
            raise ValueError("Duplicate comment IDs in batch")
        return self


class ImportResponse(BaseModel):
    imported: int


class QueueItem(BaseModel):
    comment_id: str
    video_id: str
    risk_score: float
    uncertainty: float
    model_version: str
    score_source: Literal["SIMULATED", "MODEL"]
    status: Literal["PENDING", "IN_REVIEW", "REVIEWED"]


class QueuePage(BaseModel):
    items: list[QueueItem]
    page: int
    page_size: int
    total: int
    has_next: bool


Status = Literal["PENDING", "IN_REVIEW", "REVIEWED"]
Decision = Literal["CONFIRMED_TOXIC", "NOT_TOXIC", "NEEDS_REVIEW"]


class CommentDetail(BaseModel):
    model_config = ConfigDict(json_schema_extra={"example": {
        "comment_id": "demo-1", "video_id": "video-demo", "text": "Synthetic comment",
        "risk_score": 0.72, "uncertainty": 0.28, "model_version": "logistic-tfidf-v1",
        "score_source": "MODEL", "status": "IN_REVIEW"
    }})

    comment_id: str
    video_id: str
    text: str
    risk_score: float
    uncertainty: float
    model_version: str
    score_source: Literal["SIMULATED", "MODEL"]
    status: Status


class ReviewRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True, json_schema_extra={"example": {
        "decision": "CONFIRMED_TOXIC", "notes": "Synthetic review note"
    }})

    decision: Decision
    notes: str | None = Field(default=None, max_length=2000)


class ReviewResponse(BaseModel):
    model_config = ConfigDict(json_schema_extra={"example": {
        "comment_id": "demo-1", "status": "REVIEWED", "decision": "CONFIRMED_TOXIC",
        "reviewed_by": "moderator", "reviewed_at": "2026-09-22T12:00:00+00:00"
    }})

    comment_id: str
    status: Status
    decision: Decision
    reviewed_by: str
    reviewed_at: datetime

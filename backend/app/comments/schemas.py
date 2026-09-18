"""Validated public contracts. Queue entries intentionally omit comment text."""

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

"""Supervisor ingestion and text-free queue for authenticated reviewers."""

from typing import Annotated, Literal

from fastapi import APIRouter, Depends, HTTPException, Query, Request

from app.auth.dependencies import require_roles
from app.auth.models import Role, User
from app.comments.repository import DuplicateComment
from app.comments.schemas import ImportRequest, ImportResponse, QueuePage
from app.comments.service import CommentService, ScoringUnavailable


router = APIRouter(prefix="/comments", tags=["comments"])


def get_service(request: Request) -> CommentService:
    return request.app.state.comment_service


Service = Annotated[CommentService, Depends(get_service)]
Supervisor = Annotated[User, Depends(require_roles(Role.SUPERVISOR))]
Reviewer = Annotated[User, Depends(require_roles(Role.MODERATOR, Role.SUPERVISOR))]


@router.post("/import", status_code=201, response_model=ImportResponse)
def import_comments(body: ImportRequest, service: Service, user: Supervisor) -> ImportResponse:
    try:
        return ImportResponse(imported=service.import_items(body.items))
    except DuplicateComment:
        raise HTTPException(409, "Comment ID already exists") from None
    except ScoringUnavailable:
        raise HTTPException(503, "Scoring unavailable") from None


@router.get("", response_model=QueuePage)
def queue(
    service: Service,
    user: Reviewer,
    status: Literal["PENDING"] = "PENDING",
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
) -> QueuePage:
    items, total = service.repository.page(status, page, page_size)
    return QueuePage(items=items, page=page, page_size=page_size, total=total,
                     has_next=page * page_size < total)

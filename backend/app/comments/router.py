"""Authenticated HTTP endpoints for queue, claim, reveal and history."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Request

from app.auth.dependencies import require_roles
from app.auth.models import Role, User
from app.comments.schemas import (
    ClaimResponse, CommentStatus, CommentSummary, ContentResponse,
    HistoryResponse, ImportRequest, ImportResponse, QueuePage, ReviewRequest, ReviewResponse,
)
from app.comments.repository import DuplicateComment
from app.comments.service import CommentService, ScoringUnavailable

router = APIRouter(prefix="/comments", tags=["comments"])
ReviewUser = Annotated[User, Depends(require_roles(Role.MODERATOR, Role.SUPERVISOR))]
SupervisorUser = Annotated[User, Depends(require_roles(Role.SUPERVISOR))]


def get_comment_service(request: Request) -> CommentService:
    return request.app.state.comment_service


Service = Annotated[CommentService, Depends(get_comment_service)]


@router.get("/status", response_model=list[CommentSummary])
def list_comments_by_status(user: ReviewUser, service: Service,
                            status: CommentStatus = CommentStatus.PENDING):
    return service.list_summaries(status.value)


@router.post("/import", status_code=201, response_model=ImportResponse)
def import_comments(body: ImportRequest, user: SupervisorUser, service: Service):
    try:
        return ImportResponse(imported=service.import_items(body.items))
    except DuplicateComment:
        raise HTTPException(409, "Comment ID already exists") from None
    except ScoringUnavailable:
        raise HTTPException(503, "Scoring unavailable") from None


@router.get("", response_model=QueuePage)
@router.get("/queue", response_model=QueuePage, include_in_schema=False)
def queue(user: ReviewUser, service: Service,
          page: Annotated[int, Query(ge=1)] = 1,
          page_size: Annotated[int, Query(ge=1, le=100)] = 20):
    items, total = service.repository.page("PENDING", page, page_size)
    return QueuePage(items=items, total=total, page=page, page_size=page_size,
                     has_next=page * page_size < total)


@router.post("/{comment_id}/claim", response_model=ClaimResponse)
def claim_comment(comment_id: str, user: ReviewUser, service: Service):
    return service.claim(comment_id, user)


@router.get("/{comment_id}/content", response_model=ContentResponse)
def reveal_content(comment_id: str, user: ReviewUser, service: Service):
    return service.reveal(comment_id, user)


@router.post("/{comment_id}/reviews", response_model=ReviewResponse, status_code=201)
def create_review(comment_id: str, body: ReviewRequest, user: ReviewUser, service: Service):
    return service.review(comment_id, user, body)


@router.get("/{comment_id}/history", response_model=HistoryResponse)
def get_history(comment_id: str, user: ReviewUser, service: Service):
    return service.history(comment_id)

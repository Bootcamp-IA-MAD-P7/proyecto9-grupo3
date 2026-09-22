"""Supervisor ingestion and text-free queue for authenticated reviewers."""

from typing import Annotated, Literal

from fastapi import APIRouter, Depends, HTTPException, Query, Request

from app.auth.dependencies import require_roles
from app.auth.models import Role, User
from app.comments.repository import (CommentNotFound, DuplicateComment,
                                     InvalidReviewTransition, ReviewConflict)
from app.comments.schemas import (CommentDetail, ImportRequest, ImportResponse,
                                  QueuePage, ReviewRequest, ReviewResponse)
from app.comments.service import CommentService, ScoringUnavailable


router = APIRouter(prefix="/comments", tags=["comments"])


def get_service(request: Request) -> CommentService:
    return request.app.state.comment_service


Service = Annotated[CommentService, Depends(get_service)]
Supervisor = Annotated[User, Depends(require_roles(Role.SUPERVISOR))]
Reviewer = Annotated[User, Depends(require_roles(Role.MODERATOR, Role.SUPERVISOR))]


@router.post("/import", status_code=201, response_model=ImportResponse,
             summary="Import scored comments", description="Supervisor-only batch import. Text is accepted here and never returned by the queue.",
             responses={401: {"description": "Not authenticated"}, 403: {"description": "Supervisor role required"}, 409: {"description": "Duplicate comment ID"}, 503: {"description": "Scoring unavailable"}})
def import_comments(body: ImportRequest, service: Service, user: Supervisor) -> ImportResponse:
    try:
        return ImportResponse(imported=service.import_items(body.items))
    except DuplicateComment:
        raise HTTPException(409, "Comment ID already exists") from None
    except ScoringUnavailable:
        raise HTTPException(503, "Scoring unavailable") from None


@router.get("", response_model=QueuePage, summary="List the moderation queue",
            description="Returns prioritized comments without text. Moderators and supervisors can consume the queue.",
            responses={401: {"description": "Not authenticated"}, 403: {"description": "Reviewer role required"}})
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


@router.get("/{comment_id}", response_model=CommentDetail, summary="Get comment detail",
            description="Returns the authorized review detail, including text and the original model score.",
            responses={401: {"description": "Not authenticated"}, 403: {"description": "Reviewer role required"}, 404: {"description": "Comment not found"}})
def detail(comment_id: str, service: Service, user: Reviewer) -> CommentDetail:
    try:
        return service.get_detail(comment_id)
    except CommentNotFound:
        raise HTTPException(404, "Comment not found") from None


@router.post("/{comment_id}/review", response_model=ReviewResponse, summary="Record a human review",
             description="NEEDS_REVIEW moves PENDING to IN_REVIEW. CONFIRMED_TOXIC or NOT_TOXIC finalize an IN_REVIEW comment as REVIEWED.",
             responses={400: {"description": "Invalid state transition"}, 401: {"description": "Not authenticated"},
                        403: {"description": "Reviewer role required"}, 404: {"description": "Comment not found"},
                        409: {"description": "Comment already reviewed or concurrent transition"}, 422: {"description": "Invalid review payload"}})
def review(comment_id: str, body: ReviewRequest, service: Service, user: Reviewer) -> ReviewResponse:
    try:
        return service.review(comment_id, user, body.decision, body.notes)
    except CommentNotFound:
        raise HTTPException(404, "Comment not found") from None
    except InvalidReviewTransition:
        raise HTTPException(400, "Invalid comment state transition") from None
    except ReviewConflict:
        raise HTTPException(409, "Comment already reviewed or transition conflict") from None

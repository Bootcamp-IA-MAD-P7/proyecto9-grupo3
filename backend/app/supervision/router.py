"""Supervisor-only routes; permissions come from the current database role."""

from typing import Annotated

from fastapi import APIRouter, Depends, Request

from app.auth.dependencies import require_roles
from app.auth.models import Role, User
from app.comments.schemas import CommentSummary
from app.supervision.schemas import (
    ReasonBody, ReassignBody, ReassignResponse, ReopenResponse,
    RequestStatus, ResolveBody, ResolveResponse,
)
from app.supervision.service import SupervisionService

router = APIRouter(prefix="/supervisor", tags=["supervisor"])
Supervisor = Annotated[User, Depends(require_roles(Role.SUPERVISOR))]


def get_supervision_service(request: Request) -> SupervisionService:
    return request.app.state.supervision_service


Service = Annotated[SupervisionService, Depends(get_supervision_service)]


@router.get("/escalations", response_model=list[CommentSummary])
def list_escalations(user: Supervisor, service: Service):
    return service.list_escalations()


@router.post("/comments/{comment_id}/resolve", response_model=ResolveResponse)
def resolve_comment(comment_id: str, body: ResolveBody, user: Supervisor, service: Service):
    return service.resolve(comment_id, user, body)


@router.post("/comments/{comment_id}/reassign", response_model=ReassignResponse)
def reassign_comment(comment_id: str, body: ReassignBody, user: Supervisor, service: Service):
    return service.reassign(comment_id, user, body)


@router.get("/reopen-requests", response_model=list[ReopenResponse])
def list_reopen_requests(user: Supervisor, service: Service, status: RequestStatus | None = None):
    return service.list_requests(status.value if status is not None else None)


@router.post("/reopen-requests/{request_id}/approve", response_model=ReopenResponse)
def approve_reopen(request_id: str, body: ReasonBody, user: Supervisor, service: Service):
    return service.approve(request_id, user, body.reason)


@router.post("/reopen-requests/{request_id}/reject", response_model=ReopenResponse)
def reject_reopen(request_id: str, body: ReasonBody, user: Supervisor, service: Service):
    return service.reject(request_id, user, body.reason)


@router.post("/reopen-requests/{request_id}/request-info", response_model=ReopenResponse)
def ask_for_information(request_id: str, body: ReasonBody, user: Supervisor, service: Service):
    return service.request_info(request_id, user, body.reason)

"""Human supervision use cases exposed to HTTP without leaking SQL details."""

from app.auth.models import User
from app.comments.service import CommentService
from app.supervision.repository import SupervisionRepository
from app.supervision.schemas import ReassignBody, ReopenRequestBody, ResolveBody


class SupervisionService:
    def __init__(self, repository: SupervisionRepository):
        self.repository = repository

    def list_escalations(self) -> list[dict]:
        return self.repository.list_escalations()

    def resolve(self, comment_id: str, user: User, body: ResolveBody) -> dict:
        return self.repository.resolve(comment_id, user, body.reason, body.recommend_removal)

    def reassign(self, comment_id: str, user: User, body: ReassignBody) -> dict:
        return self.repository.reassign(
            comment_id, user, body.reviewer_id, body.reason,
            CommentService.CLAIM_LEASE_SECONDS,
        )

    def request_reopen(self, comment_id: str, user: User, body: ReopenRequestBody) -> dict:
        return self.repository.create_request(comment_id, user, body.reason, body.optional_note)

    def list_requests(self, status: str | None = None, comment_id: str | None = None) -> list[dict]:
        return self.repository.list_requests(status, comment_id)

    def approve(self, request_id: str, user: User, reason: str) -> dict:
        return self.repository.decide(request_id, user, reason, approve=True)

    def reject(self, request_id: str, user: User, reason: str) -> dict:
        return self.repository.decide(request_id, user, reason, approve=False)

    def request_info(self, request_id: str, user: User, note: str) -> dict:
        return self.repository.request_info(request_id, user, note)

    def provide_info(self, comment_id: str, request_id: str, user: User, note: str) -> dict:
        return self.repository.provide_info(comment_id, request_id, user, note)

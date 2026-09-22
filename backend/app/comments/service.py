"""Apply scoring to a validated batch before its single database transaction."""

from app.auth.models import User
from app.comments.repository import CommentRepository
from app.comments.schemas import CommentDetail, Decision, ImportItem, ReviewResponse
from app.comments.scoring import Scorer


class ScoringUnavailable(Exception):
    pass


class CommentService:
    def __init__(self, repository: CommentRepository, scorer: Scorer):
        self.repository = repository
        self.scorer = scorer

    def import_items(self, items: list[ImportItem]) -> int:
        try:
            scored = [(item, self.scorer.score_comment(item.text)) for item in items]
        except Exception as error:
            raise ScoringUnavailable from error
        self.repository.insert_batch(scored)
        return len(scored)

    def get_detail(self, comment_id: str) -> CommentDetail:
        return self.repository.detail(comment_id)

    def review(self, comment_id: str, user: User, decision: Decision,
               notes: str | None) -> ReviewResponse:
        return self.repository.review(comment_id, user, decision, notes)

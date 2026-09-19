"""Human review rules independent of HTTP and SQL representation."""

from app.auth.models import User
from app.comments.repository import CommentRepository
from app.comments.schemas import ReviewRequest, ReviewResult
from app.comments.scoring import Scorer


class ScoringUnavailable(Exception):
    pass


class CommentService:
    CLAIM_LEASE_SECONDS = 15 * 60

    def __init__(self, repository: CommentRepository, scorer: Scorer):
        self.repository = repository
        self.scorer = scorer

    def import_items(self, items) -> int:
        try:
            records = []
            for item in items:
                score = self.scorer.score_comment(item.text)
                records.append((item.comment_id, item.video_id, item.text,
                                score.risk_score, score.uncertainty,
                                score.model_version, score.score_source))
        except Exception as error:
            raise ScoringUnavailable() from error
        return self.repository.insert_batch(records)

    def list_summaries(self, status: str) -> list[dict]:
        return self.repository.list_summaries(status)

    def claim(self, comment_id: str, user: User) -> dict:
        return self.repository.claim(comment_id, user, self.CLAIM_LEASE_SECONDS)

    def reveal(self, comment_id: str, user: User) -> dict:
        return self.repository.reveal(comment_id, user)

    def review(self, comment_id: str, user: User, request: ReviewRequest) -> dict:
        if request.result == ReviewResult.NO_ESCALATION:
            status, event_type = "CLASSIFIED", "classified"
        else:
            status, event_type = "ESCALATED", "escalated"
        return self.repository.save_review(
            comment_id, user, request.result.value, request.reason, status, event_type
        )

    def history(self, comment_id: str) -> dict:
        return self.repository.history(comment_id)

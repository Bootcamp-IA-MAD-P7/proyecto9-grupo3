"""Apply scoring to a validated batch before its single database transaction."""

from app.comments.repository import CommentRepository
from app.comments.schemas import ImportItem
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

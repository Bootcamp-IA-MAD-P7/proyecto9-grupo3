"""Atomic writes and deterministic queue queries."""

import sqlite3

from datetime import datetime, timezone

from app.auth.models import User
from app.comments.schemas import CommentDetail, Decision, ImportItem, QueueItem, ReviewResponse
from app.comments.scoring import Score
from app.database import Database


class DuplicateComment(Exception):
    pass


class CommentNotFound(Exception):
    pass


class InvalidReviewTransition(Exception):
    pass


class ReviewConflict(Exception):
    pass


class CommentRepository:
    def __init__(self, database: Database):
        self.database = database

    def insert_batch(self, records: list[tuple[ImportItem, Score]]) -> None:
        try:
            with self.database.connect() as connection:
                connection.execute("BEGIN IMMEDIATE")
                connection.executemany("""
                    INSERT INTO comments(comment_id, video_id, text, risk_score, uncertainty, model_version, score_source)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, [
                    (item.comment_id, item.video_id, item.text, score.risk_score,
                     score.uncertainty, score.model_version, score.score_source)
                    for item, score in records
                ])
        except sqlite3.IntegrityError as error:
            if "comments.comment_id" in str(error):
                raise DuplicateComment from None
            raise

    def page(self, status: str, page: int, page_size: int) -> tuple[list[QueueItem], int]:
        with self.database.connect() as connection:
            connection.execute("BEGIN")
            total = connection.execute(
                "SELECT count(*) FROM comments WHERE status=? AND risk_score IS NOT NULL", (status,)
            ).fetchone()[0]
            rows = connection.execute("""
                SELECT comment_id, video_id, risk_score, uncertainty, model_version, score_source, status
                FROM comments WHERE status=? AND risk_score IS NOT NULL
                ORDER BY risk_score DESC, sequence ASC LIMIT ? OFFSET ?
            """, (status, page_size, (page - 1) * page_size)).fetchall()
            return [QueueItem.model_validate(dict(row)) for row in rows], total

    def detail(self, comment_id: str) -> CommentDetail:
        with self.database.connect() as connection:
            row = connection.execute("""
                SELECT comment_id, video_id, text, risk_score, uncertainty,
                       model_version, score_source, status
                FROM comments WHERE comment_id=?
            """, (comment_id,)).fetchone()
        if row is None:
            raise CommentNotFound
        return CommentDetail.model_validate(dict(row))

    def review(self, comment_id: str, user: User, decision: Decision,
               notes: str | None) -> ReviewResponse:
        reviewed_at = datetime.now(timezone.utc)
        with self.database.connect() as connection:
            row = connection.execute(
                "SELECT status FROM comments WHERE comment_id=?", (comment_id,)
            ).fetchone()
            if row is None:
                raise CommentNotFound
            status = row["status"]
            if status == "REVIEWED":
                raise ReviewConflict
            if status == "PENDING" and decision != "NEEDS_REVIEW":
                raise InvalidReviewTransition
            if status not in {"PENDING", "IN_REVIEW"}:
                raise InvalidReviewTransition
            next_status = "IN_REVIEW" if decision == "NEEDS_REVIEW" else "REVIEWED"
            connection.execute("""
                UPDATE comments
                SET status=?, review_decision=?, reviewed_by=?, reviewed_at=?, review_notes=?
                WHERE comment_id=? AND status=?
            """, (next_status, decision, user.id, reviewed_at.isoformat(), notes,
                  comment_id, status))
            if connection.total_changes != 1:
                raise ReviewConflict
        return ReviewResponse(comment_id=comment_id, status=next_status, decision=decision,
                              reviewed_by=user.username, reviewed_at=reviewed_at)

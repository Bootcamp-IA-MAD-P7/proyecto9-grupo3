"""Atomic writes and deterministic queue queries."""

import sqlite3

from app.comments.schemas import ImportItem, QueueItem
from app.comments.scoring import Score
from app.database import Database


class DuplicateComment(Exception):
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

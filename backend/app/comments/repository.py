"""SQLite transactions for queue, exclusive claims and append-only review."""

import sqlite3
import time
import uuid

from app.auth.models import User
from app.database import Database


class CommentError(Exception):
    status_code = 500
    detail = "Comment operation failed"


class CommentNotFound(CommentError):
    status_code = 404
    detail = "Comment not found"


class CommentConflict(CommentError):
    status_code = 409
    detail = "Comment is not available for this operation"


class NotAssignee(CommentError):
    status_code = 403
    detail = "Current assignment is required"


class DuplicateComment(CommentError):
    status_code = 409
    detail = "Comment ID already exists"


class CommentRepository:
    def __init__(self, database: Database):
        self.database = database

    @staticmethod
    def _now() -> int:
        return int(time.time())

    @staticmethod
    def _expire_claims(connection: sqlite3.Connection, now: int) -> None:
        expired = connection.execute(
            """SELECT id, comment_id, return_status FROM assignments
               WHERE closed_at IS NULL AND expires_at<=?""",
            (now,),
        ).fetchall()
        for assignment in expired:
            connection.execute(
                "UPDATE assignments SET closed_at=? WHERE id=?", (now, assignment["id"])
            )
            connection.execute(
                "UPDATE comments SET status=? WHERE id=? AND status='IN_REVIEW'",
                (assignment["return_status"], assignment["comment_id"]),
            )
            connection.execute(
                """INSERT INTO audit_events(comment_id, event_type, created_at)
                   VALUES (?, 'claim_expired', ?)""",
                (assignment["comment_id"], now),
            )

    @staticmethod
    def _comment(connection: sqlite3.Connection, comment_id: str) -> sqlite3.Row:
        row = connection.execute("SELECT * FROM comments WHERE id=?", (comment_id,)).fetchone()
        if row is None:
            raise CommentNotFound()
        return row

    @staticmethod
    def _active_assignment(connection: sqlite3.Connection, comment_id: str) -> sqlite3.Row | None:
        return connection.execute(
            """SELECT * FROM assignments
               WHERE comment_id=? AND closed_at IS NULL""",
            (comment_id,),
        ).fetchone()

    def insert_batch(self, items: list[tuple]) -> int:
        with self.database.connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            next_order = connection.execute(
                "SELECT COALESCE(MAX(source_order), 0) + 1 FROM comments"
            ).fetchone()[0]
            try:
                connection.executemany("""INSERT INTO comments
                    (id, video_id, text, risk_score, uncertainty, model_version,
                     score_source, source_order)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)""", [
                    (*item, next_order + index) for index, item in enumerate(items)
                ])
            except sqlite3.IntegrityError as error:
                raise DuplicateComment() from error
        return len(items)

    def page(self, status: str, page: int, page_size: int) -> tuple[list[dict], int]:
        with self.database.connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            self._expire_claims(connection, self._now())
            total = connection.execute(
                "SELECT count(*) FROM comments WHERE status=?", (status,)
            ).fetchone()[0]
            rows = connection.execute("""SELECT id AS comment_id, video_id,
                risk_score, uncertainty, model_version, score_source, status
                FROM comments WHERE status=?
                ORDER BY risk_score DESC, source_order ASC LIMIT ? OFFSET ?""",
                (status, page_size, (page - 1) * page_size),
            ).fetchall()
            return [dict(row) for row in rows], total

    def assigned_to(self, user_id: str) -> list[dict]:
        with self.database.connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            self._expire_claims(connection, self._now())
            rows = connection.execute("""SELECT c.id AS comment_id, c.video_id,
                c.risk_score, c.model_version, c.status FROM comments c
                JOIN assignments a ON a.comment_id=c.id
                WHERE a.reviewer_id=? AND a.closed_at IS NULL AND c.status='IN_REVIEW'
                ORDER BY a.claimed_at DESC, a.id DESC""", (user_id,)).fetchall()
            return [dict(row) for row in rows]

    def list_summaries(self, status: str) -> list[dict]:
        with self.database.connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            now = self._now()
            self._expire_claims(connection, now)
            rows = connection.execute(
                """SELECT id AS comment_id, video_id, risk_score, model_version, status
                   FROM comments WHERE status=?
                   ORDER BY risk_score DESC, source_order ASC""",
                (status,),
            ).fetchall()
            return [dict(row) for row in rows]

    def claim(self, comment_id: str, user: User, lease_seconds: int) -> dict:
        with self.database.connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            now = self._now()
            self._expire_claims(connection, now)
            comment = self._comment(connection, comment_id)
            if comment["status"] != "PENDING":
                raise CommentConflict()
            changed = connection.execute(
                "UPDATE comments SET status='IN_REVIEW' WHERE id=? AND status='PENDING'",
                (comment_id,),
            ).rowcount
            if changed != 1:
                raise CommentConflict()
            expires_at = now + lease_seconds
            connection.execute(
                """INSERT INTO assignments(comment_id, reviewer_id, claimed_at, expires_at)
                   VALUES (?, ?, ?, ?)""",
                (comment_id, user.id, now, expires_at),
            )
            connection.execute(
                """INSERT INTO audit_events
                   (comment_id, actor_id, actor_display_name, event_type, created_at)
                   VALUES (?, ?, ?, 'assigned', ?)""",
                (comment_id, user.id, user.display_name, now),
            )
            return {"comment_id": comment_id, "status": "IN_REVIEW", "claim_expires_at": expires_at}

    def reveal(self, comment_id: str, user: User) -> dict:
        with self.database.connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            now = self._now()
            self._expire_claims(connection, now)
            comment = self._comment(connection, comment_id)
            assignment = self._active_assignment(connection, comment_id)
            if assignment is None or assignment["reviewer_id"] != user.id:
                raise NotAssignee()
            connection.execute(
                """INSERT INTO audit_events
                   (comment_id, actor_id, actor_display_name, event_type, created_at)
                   VALUES (?, ?, ?, 'content_revealed', ?)""",
                (comment_id, user.id, user.display_name, now),
            )
            return {"comment_id": comment_id, "text": comment["text"]}

    def save_review(
        self, comment_id: str, user: User, result: str, reason: str, status: str, event_type: str
    ) -> dict:
        with self.database.connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            now = self._now()
            self._expire_claims(connection, now)
            comment = self._comment(connection, comment_id)
            assignment = self._active_assignment(connection, comment_id)
            if assignment is None or comment["status"] != "IN_REVIEW":
                raise CommentConflict()
            if assignment["reviewer_id"] != user.id:
                raise NotAssignee()
            review_id = str(uuid.uuid4())
            connection.execute(
                """INSERT INTO reviews
                   (id, assignment_id, comment_id, reviewer_id,
                    reviewer_display_name, result, reason, created_at,
                    model_score, model_version)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    review_id, assignment["id"], comment_id, user.id,
                    user.display_name, result, reason, now,
                    comment["risk_score"], comment["model_version"],
                ),
            )
            connection.execute("UPDATE assignments SET closed_at=? WHERE id=?", (now, assignment["id"]))
            connection.execute("UPDATE comments SET status=? WHERE id=?", (status, comment_id))
            connection.execute(
                """INSERT INTO audit_events
                   (comment_id, actor_id, actor_display_name, event_type, created_at, review_id)
                   VALUES (?, ?, ?, ?, ?, ?)""",
                (comment_id, user.id, user.display_name, event_type, now, review_id),
            )
            return {
                "review_id": review_id, "comment_id": comment_id,
                "reviewer_id": user.id, "reviewer_display_name": user.display_name,
                "result": result, "reason": reason, "created_at": now,
                "model_score": comment["risk_score"],
                "model_version": comment["model_version"], "status": status,
            }

    def history(self, comment_id: str) -> dict:
        with self.database.connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            now = self._now()
            self._expire_claims(connection, now)
            comment = self._comment(connection, comment_id)
            events = connection.execute(
                """SELECT audit_events.event_type, audit_events.actor_id,
                          audit_events.actor_display_name,
                          audit_events.created_at, reviews.result,
                          COALESCE(reviews.reason, reopen_updates.note,
                              CASE WHEN event_type='reopen_requested'
                                   THEN reopen_requests.reason
                                   WHEN event_type IN ('reopen_approved', 'reopen_rejected')
                                   THEN reopen_requests.decision_reason
                                   ELSE supervisor_actions.reason END) AS reason,
                          reviews.model_score, reviews.model_version,
                          supervisor_actions.target_user_id AS target_reviewer_id,
                          supervisor_actions.recommend_removal
                   FROM audit_events LEFT JOIN reviews ON reviews.id=audit_events.review_id
                   LEFT JOIN reopen_requests ON reopen_requests.id=audit_events.reopen_request_id
                   LEFT JOIN reopen_updates ON reopen_updates.id=audit_events.reopen_update_id
                   LEFT JOIN supervisor_actions ON supervisor_actions.id=audit_events.supervisor_action_id
                   WHERE audit_events.comment_id=? ORDER BY audit_events.id""",
                (comment_id,),
            ).fetchall()
            return {
                "comment_id": comment_id,
                "status": comment["status"],
                "events": [dict(event) for event in events],
            }

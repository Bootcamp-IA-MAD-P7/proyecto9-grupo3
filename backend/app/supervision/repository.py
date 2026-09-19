"""Transactional supervisor transitions and reopening records."""

import sqlite3
import time
import uuid

from app.auth.models import User
from app.comments.repository import CommentConflict, CommentError, CommentNotFound, CommentRepository
from app.database import Database


class ReopenRequestNotFound(CommentError):
    status_code = 404
    detail = "Reopen request not found"


class TargetUserNotFound(CommentError):
    status_code = 404
    detail = "Active staff user not found"


class NotRequester(CommentError):
    status_code = 403
    detail = "Only the original requester can provide information"


class SupervisionRepository:
    def __init__(self, database: Database):
        self.database = database

    @staticmethod
    def _now() -> int:
        return int(time.time())

    @staticmethod
    def _comment(connection: sqlite3.Connection, comment_id: str) -> sqlite3.Row:
        row = connection.execute("SELECT * FROM comments WHERE id=?", (comment_id,)).fetchone()
        if row is None:
            raise CommentNotFound()
        return row

    @staticmethod
    def _request(connection: sqlite3.Connection, request_id: str) -> sqlite3.Row:
        row = connection.execute("SELECT * FROM reopen_requests WHERE id=?", (request_id,)).fetchone()
        if row is None:
            raise ReopenRequestNotFound()
        return row

    @staticmethod
    def _view(connection: sqlite3.Connection, row: sqlite3.Row) -> dict:
        updates = connection.execute(
            """SELECT id, actor_id, kind, note, created_at FROM reopen_updates
               WHERE request_id=? ORDER BY seq""", (row["id"],)
        ).fetchall()
        return {
            "request_id": row["id"], "comment_id": row["comment_id"],
            "requested_by": row["requested_by"], "reason": row["reason"],
            "optional_note": row["optional_note"], "requested_at": row["requested_at"],
            "previous_status": row["previous_status"], "status": row["status"],
            "decided_by": row["decided_by"], "decided_at": row["decided_at"],
            "decision_reason": row["decision_reason"],
            "updates": [dict(update) for update in updates],
        }

    @staticmethod
    def _audit(
        connection: sqlite3.Connection, comment_id: str, user: User,
        event_type: str, now: int, *, request_id: str | None = None,
        update_id: str | None = None, action_id: str | None = None,
    ) -> None:
        connection.execute(
            """INSERT INTO audit_events
               (comment_id, actor_id, actor_display_name, event_type, created_at,
                reopen_request_id, reopen_update_id, supervisor_action_id)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (comment_id, user.id, user.display_name, event_type, now,
             request_id, update_id, action_id),
        )

    def list_escalations(self) -> list[dict]:
        with self.database.connect() as connection:
            rows = connection.execute(
                """SELECT id AS comment_id, video_id, risk_score, model_version, status
                   FROM comments WHERE status='ESCALATED'
                   ORDER BY risk_score DESC, source_order"""
            ).fetchall()
            return [dict(row) for row in rows]

    def resolve(self, comment_id: str, user: User, reason: str, recommend_removal: bool) -> dict:
        with self.database.connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            now = self._now()
            comment = self._comment(connection, comment_id)
            if comment["status"] != "ESCALATED":
                raise CommentConflict()
            action_id = str(uuid.uuid4())
            connection.execute(
                """INSERT INTO supervisor_actions
                   (id, comment_id, actor_id, action_type, reason, recommend_removal, created_at)
                   VALUES (?, ?, ?, 'RESOLVE', ?, ?, ?)""",
                (action_id, comment_id, user.id, reason, int(recommend_removal), now),
            )
            connection.execute("UPDATE comments SET status='RESOLVED' WHERE id=?", (comment_id,))
            self._audit(connection, comment_id, user, "resolved", now, action_id=action_id)
            return {
                "action_id": action_id, "comment_id": comment_id, "status": "RESOLVED",
                "reason": reason, "recommend_removal": recommend_removal,
            }

    def reassign(self, comment_id: str, user: User, reviewer_id: str, reason: str, lease_seconds: int) -> dict:
        with self.database.connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            now = self._now()
            CommentRepository._expire_claims(connection, now)
            comment = self._comment(connection, comment_id)
            if comment["status"] not in {"ESCALATED", "REOPENED", "IN_REVIEW"}:
                raise CommentConflict()
            target = connection.execute(
                "SELECT id FROM users WHERE id=? AND is_active=1", (reviewer_id,)
            ).fetchone()
            if target is None:
                raise TargetUserNotFound()
            active = CommentRepository._active_assignment(connection, comment_id)
            return_status = active["return_status"] if active is not None else comment["status"]
            if active is not None:
                if active["reviewer_id"] == reviewer_id:
                    raise CommentConflict()
                connection.execute("UPDATE assignments SET closed_at=? WHERE id=?", (now, active["id"]))
            expires_at = now + lease_seconds
            connection.execute(
                """INSERT INTO assignments(comment_id, reviewer_id, claimed_at, expires_at, return_status)
                   VALUES (?, ?, ?, ?, ?)""", (comment_id, reviewer_id, now, expires_at, return_status)
            )
            connection.execute("UPDATE comments SET status='IN_REVIEW' WHERE id=?", (comment_id,))
            action_id = str(uuid.uuid4())
            connection.execute(
                """INSERT INTO supervisor_actions
                   (id, comment_id, actor_id, action_type, reason, target_user_id, created_at)
                   VALUES (?, ?, ?, 'REASSIGN', ?, ?, ?)""",
                (action_id, comment_id, user.id, reason, reviewer_id, now),
            )
            self._audit(connection, comment_id, user, "reassigned", now, action_id=action_id)
            return {
                "action_id": action_id, "comment_id": comment_id, "status": "IN_REVIEW",
                "reviewer_id": reviewer_id, "claim_expires_at": expires_at,
            }

    def create_request(self, comment_id: str, user: User, reason: str, optional_note: str | None) -> dict:
        with self.database.connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            now = self._now()
            comment = self._comment(connection, comment_id)
            if comment["status"] not in {"CLASSIFIED", "RESOLVED"}:
                raise CommentConflict()
            request_id = str(uuid.uuid4())
            connection.execute(
                """INSERT INTO reopen_requests
                   (id, comment_id, requested_by, reason, optional_note, requested_at,
                    previous_status, status)
                   VALUES (?, ?, ?, ?, ?, ?, ?, 'PENDING')""",
                (request_id, comment_id, user.id, reason, optional_note, now, comment["status"]),
            )
            connection.execute("UPDATE comments SET status='REOPEN_REQUESTED' WHERE id=?", (comment_id,))
            self._audit(connection, comment_id, user, "reopen_requested", now, request_id=request_id)
            return self._view(connection, self._request(connection, request_id))

    def list_requests(self, status: str | None = None, comment_id: str | None = None) -> list[dict]:
        with self.database.connect() as connection:
            if comment_id is not None:
                self._comment(connection, comment_id)
            rows = connection.execute(
                """SELECT * FROM reopen_requests
                   WHERE (? IS NULL OR status=?) AND (? IS NULL OR comment_id=?)
                   ORDER BY requested_at, rowid""",
                (status, status, comment_id, comment_id),
            ).fetchall()
            return [self._view(connection, row) for row in rows]

    def decide(self, request_id: str, user: User, reason: str, approve: bool) -> dict:
        with self.database.connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            now = self._now()
            row = self._request(connection, request_id)
            if row["status"] not in ({"PENDING"} if approve else {"PENDING", "NEEDS_INFO"}):
                raise CommentConflict()
            comment = self._comment(connection, row["comment_id"])
            if comment["status"] != "REOPEN_REQUESTED":
                raise CommentConflict()
            request_status = "APPROVED" if approve else "REJECTED"
            comment_status = "REOPENED" if approve else row["previous_status"]
            connection.execute(
                """UPDATE reopen_requests
                   SET status=?, decided_by=?, decided_at=?, decision_reason=? WHERE id=?""",
                (request_status, user.id, now, reason, request_id),
            )
            connection.execute(
                "UPDATE comments SET status=? WHERE id=?", (comment_status, row["comment_id"])
            )
            self._audit(
                connection, row["comment_id"], user,
                "reopen_approved" if approve else "reopen_rejected", now,
                request_id=request_id,
            )
            return self._view(connection, self._request(connection, request_id))

    def request_info(self, request_id: str, user: User, note: str) -> dict:
        with self.database.connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            now = self._now()
            row = self._request(connection, request_id)
            if row["status"] != "PENDING":
                raise CommentConflict()
            update_id = str(uuid.uuid4())
            connection.execute(
                """INSERT INTO reopen_updates(id, request_id, actor_id, kind, note, created_at)
                   VALUES (?, ?, ?, 'INFO_REQUESTED', ?, ?)""",
                (update_id, request_id, user.id, note, now),
            )
            connection.execute(
                "UPDATE reopen_requests SET status='NEEDS_INFO' WHERE id=?", (request_id,)
            )
            self._audit(connection, row["comment_id"], user, "reopen_info_requested", now,
                        request_id=request_id, update_id=update_id)
            return self._view(connection, self._request(connection, request_id))

    def provide_info(self, comment_id: str, request_id: str, user: User, note: str) -> dict:
        with self.database.connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            now = self._now()
            row = self._request(connection, request_id)
            if row["comment_id"] != comment_id:
                raise ReopenRequestNotFound()
            if row["requested_by"] != user.id:
                raise NotRequester()
            if row["status"] != "NEEDS_INFO":
                raise CommentConflict()
            update_id = str(uuid.uuid4())
            connection.execute(
                """INSERT INTO reopen_updates(id, request_id, actor_id, kind, note, created_at)
                   VALUES (?, ?, ?, 'INFO_PROVIDED', ?, ?)""",
                (update_id, request_id, user.id, note, now),
            )
            connection.execute("UPDATE reopen_requests SET status='PENDING' WHERE id=?", (request_id,))
            self._audit(connection, comment_id, user, "reopen_info_provided", now,
                        request_id=request_id, update_id=update_id)
            return self._view(connection, self._request(connection, request_id))

"""Supervisor contracts against a real SQLite database and HTTP app."""

import sqlite3
import time
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier

import pytest
from fastapi.testclient import TestClient
from pwdlib import PasswordHash

from app.database import Database
from app.comments.repository import CommentRepository
from app.main import create_app
from app.seed_demo_users import seed_demo_users


PASSWORD = "Synthetic-supervision-password-42!"
TEXT = "Synthetic private comment text for supervision tests."


def auth(token):
    return {"Authorization": f"Bearer {token}"}


def login(client, username):
    response = client.post("/auth/login", json={"username": username, "password": PASSWORD})
    assert response.status_code == 200
    return response.json()["access_token"]


def review(client, token, comment_id, result):
    assert client.post(f"/comments/{comment_id}/claim", headers=auth(token)).status_code == 200
    response = client.post(
        f"/comments/{comment_id}/reviews", headers=auth(token),
        json={"result": result, "reason": "Human decision on synthetic example"},
    )
    assert response.status_code == 201
    return response.json()


@pytest.fixture
def scenario(monkeypatch, tmp_path):
    monkeypatch.setenv("MODERATION_DATABASE_PATH", str(tmp_path / "supervision.db"))
    app = create_app()
    with TestClient(app) as client:
        database = app.state.database
        seed_demo_users(database, PASSWORD, PASSWORD)
        with database.connect() as connection:
            connection.execute(
                """INSERT INTO users(id, username, display_name, password_hash, role, created_at)
                   VALUES ('u-second', 'second', 'Second Moderator', ?, 'MODERATOR', ?)""",
                (PasswordHash.recommended().hash(PASSWORD), int(time.time())),
            )
            for order, comment_id in enumerate(("C-1", "C-2", "C-3"), 1):
                connection.execute(
                    """INSERT INTO comments
                       (id, video_id, text, risk_score, model_version, source_order)
                       VALUES (?, 'V-1', ?, 0.8, 'demo-simulated-v1', ?)""",
                    (comment_id, TEXT, order),
                )
        yield client, database, login(client, "moderator"), login(client, "supervisor"), login(client, "second")


def test_v2_migration_preserves_existing_review_and_audit(tmp_path):
    path = tmp_path / "v2.db"
    db = Database(path)
    with db.connect() as connection:
        db._create_auth_schema(connection)
        db._create_review_schema(connection)
        connection.execute("PRAGMA user_version=2")
        connection.execute(
            """INSERT INTO users(id, username, display_name, password_hash, role, created_at)
               VALUES ('u-1', 'moderator', 'Moderator', 'synthetic-hash', 'MODERATOR', 1)"""
        )
        connection.execute(
            """INSERT INTO comments(id, video_id, text, risk_score, model_version, source_order,
                                    status) VALUES ('C-1', 'V-1', ?, 0.8, 'demo-v1', 1, 'CLASSIFIED')""",
            (TEXT,),
        )
        connection.execute(
            """INSERT INTO assignments(comment_id, reviewer_id, claimed_at, expires_at, closed_at)
               VALUES ('C-1', 'u-1', 1, 2, 2)"""
        )
        connection.execute(
            """INSERT INTO reviews(id, assignment_id, comment_id, reviewer_id, reviewer_display_name,
                                   result, reason, created_at, model_score, model_version)
               VALUES ('r-1', 1, 'C-1', 'u-1', 'Moderator', 'NO_ESCALATION',
                       'Prior human decision', 2, 0.8, 'demo-v1')"""
        )
        connection.execute(
            """INSERT INTO audit_events(comment_id, actor_id, actor_display_name,
                                        event_type, created_at, review_id)
               VALUES ('C-1', 'u-1', 'Moderator', 'classified', 2, 'r-1')"""
        )
    db.initialize()
    db.initialize()
    with db.connect() as connection:
        assert connection.execute("PRAGMA user_version").fetchone()[0] == 5
        assert connection.execute("SELECT reason FROM reviews WHERE id='r-1'").fetchone()[0] == "Prior human decision"
        assert connection.execute("SELECT event_type FROM audit_events WHERE review_id='r-1'").fetchone()[0] == "classified"
        assert connection.execute("SELECT count(*) FROM reopen_requests").fetchone()[0] == 0
        assert connection.execute("PRAGMA foreign_key_check").fetchall() == []


def test_v3_migration_adds_return_state_without_losing_claims(tmp_path):
    db = Database(tmp_path / "v3.db")
    with db.connect() as connection:
        db._create_auth_schema(connection)
        db._create_review_schema(connection)
        db._create_supervision_schema(connection)
        db._migrate_audit_events(connection)
        connection.execute("PRAGMA user_version=3")
        connection.execute(
            """INSERT INTO users(id, username, display_name, password_hash, role, created_at)
               VALUES ('u-1', 'staff', 'Staff', 'synthetic-hash', 'MODERATOR', 1)"""
        )
        connection.execute(
            """INSERT INTO comments(id, video_id, text, risk_score, model_version, source_order,
                                    status) VALUES ('C-1', 'V-1', ?, 0.8, 'demo-v1', 1, 'IN_REVIEW')""",
            (TEXT,),
        )
        connection.execute(
            """INSERT INTO assignments(comment_id, reviewer_id, claimed_at, expires_at)
               VALUES ('C-1', 'u-1', 1, 9999999999)"""
        )
    db.initialize()
    with db.connect() as connection:
        assert connection.execute("PRAGMA user_version").fetchone()[0] == 5
        assert connection.execute("SELECT return_status FROM assignments").fetchone()[0] == "PENDING"
        assert connection.execute("PRAGMA foreign_key_check").fetchall() == []


@pytest.mark.parametrize("origin", ["ESCALATED", "REOPENED"])
def test_supervisor_assignment_expiry_restores_controlled_state(scenario, origin, monkeypatch):
    client, db, moderator, supervisor, second = scenario
    if origin == "ESCALATED":
        review(client, moderator, "C-1", "ESCALATE_TO_SUPERVISOR")
    else:
        review(client, moderator, "C-1", "NO_ESCALATION")
        request_id = client.post(
            "/comments/C-1/reopen-requests", headers=auth(moderator),
            json={"reason": "Check again"},
        ).json()["request_id"]
        assert client.post(
            f"/supervisor/reopen-requests/{request_id}/approve",
            headers=auth(supervisor), json={"reason": "Approved"},
        ).status_code == 200
    reviewer_id = client.get("/auth/me", headers=auth(second)).json()["id"]
    assert client.post(
        "/supervisor/comments/C-1/reassign", headers=auth(supervisor),
        json={"reviewer_id": reviewer_id, "reason": "Directed review"},
    ).status_code == 200
    monkeypatch.setattr(CommentRepository, "_now", staticmethod(lambda: int(time.time()) + 1000))
    assert client.get("/comments", headers=auth(moderator)).status_code == 200
    history = client.get("/comments/C-1/history", headers=auth(moderator)).json()
    assert history["status"] == origin
    assert client.post("/comments/C-1/claim", headers=auth(moderator)).status_code == 409
    with db.connect() as connection:
        assert connection.execute(
            "SELECT count(*) FROM assignments WHERE comment_id='C-1' AND closed_at IS NULL"
        ).fetchone()[0] == 0


def test_supervisor_resolves_escalation_and_moderator_cannot(scenario):
    client, db, moderator, supervisor, _ = scenario
    review(client, moderator, "C-1", "ESCALATE_TO_SUPERVISOR")
    assert client.get("/supervisor/escalations").status_code == 401
    assert client.get("/supervisor/escalations", headers=auth(moderator)).status_code == 403
    listed = client.get("/supervisor/escalations", headers=auth(supervisor))
    assert listed.status_code == 200 and [row["comment_id"] for row in listed.json()] == ["C-1"]
    assert TEXT not in listed.text
    url = "/supervisor/comments/C-1/resolve"
    payload = {"reason": "Supervisor recommends local removal review", "recommend_removal": True}
    assert client.post(url, headers=auth(moderator), json=payload).status_code == 403
    resolved = client.post(url, headers=auth(supervisor), json=payload)
    assert resolved.status_code == 200
    assert resolved.json()["status"] == "RESOLVED"
    assert resolved.json()["recommend_removal"] is True
    assert client.post(url, headers=auth(supervisor), json=payload).status_code == 409
    assert client.get("/supervisor/escalations", headers=auth(supervisor)).json() == []
    history = client.get("/comments/C-1/history", headers=auth(moderator))
    assert [item["event_type"] for item in history.json()["events"]][-2:] == ["escalated", "resolved"]
    assert history.json()["events"][-1]["reason"] == payload["reason"]
    assert TEXT not in history.text
    with db.connect() as connection:
        assert TEXT not in repr([tuple(row) for row in connection.execute("SELECT * FROM audit_events")])


def test_supervisor_reassigns_escalated_and_active_work(scenario):
    client, db, moderator, supervisor, second = scenario
    review(client, moderator, "C-1", "TRANSFER_REQUESTED")
    target_id = client.get("/auth/me", headers=auth(second)).json()["id"]
    url = "/supervisor/comments/C-1/reassign"
    payload = {"reviewer_id": target_id, "reason": "Transfer to second moderator"}
    assert client.post(url, headers=auth(moderator), json=payload).status_code == 403
    assert client.post(url, headers=auth(supervisor), json={**payload, "reviewer_id": "missing"}).status_code == 404
    assigned = client.post(url, headers=auth(supervisor), json=payload)
    assert assigned.status_code == 200 and assigned.json()["status"] == "IN_REVIEW"
    assert assigned.json()["reviewer_id"] == target_id
    assert client.post(url, headers=auth(supervisor), json=payload).status_code == 409
    assert client.get("/comments/C-1/content", headers=auth(moderator)).status_code == 403
    assert client.get("/comments/C-1/content", headers=auth(second)).status_code == 200
    assert client.post("/comments/C-2/claim", headers=auth(moderator)).status_code == 200
    reassigned = client.post("/supervisor/comments/C-2/reassign", headers=auth(supervisor), json=payload)
    assert reassigned.status_code == 200
    assert client.post("/comments/C-2/reviews", headers=auth(moderator), json={"result": "NO_ESCALATION", "reason": "Old owner"}).status_code == 403
    assert client.post("/comments/C-2/reviews", headers=auth(second), json={"result": "NO_ESCALATION", "reason": "New owner"}).status_code == 201
    with db.connect() as connection:
        assert connection.execute("SELECT count(*) FROM assignments WHERE comment_id='C-2' AND closed_at IS NULL").fetchone()[0] == 0


def test_reopen_requires_supervisor_approval_then_reassignment(scenario):
    client, db, moderator, supervisor, second = scenario
    old = review(client, moderator, "C-1", "NO_ESCALATION")
    url = "/comments/C-1/reopen-requests"
    requested = client.post(url, headers=auth(second), json={"reason": "Check context", "optional_note": "Synthetic follow-up"})
    assert requested.status_code == 201 and requested.json()["status"] == "PENDING"
    request_id = requested.json()["request_id"]
    assert client.post(url, headers=auth(second), json={"reason": "Duplicate"}).status_code == 409
    assert client.get("/comments/C-1/history", headers=auth(moderator)).json()["status"] == "REOPEN_REQUESTED"
    assert "C-1" not in [item["comment_id"] for item in client.get("/comments", headers=auth(moderator)).json()["items"]]
    assert client.post("/comments/C-1/claim", headers=auth(second)).status_code == 409
    approve = f"/supervisor/reopen-requests/{request_id}/approve"
    assert client.post(approve, headers=auth(moderator), json={"reason": "Approve"}).status_code == 403
    assert client.post(approve, headers=auth(supervisor), json={"reason": "Approve after human review"}).status_code == 200
    assert client.get("/comments/C-1/history", headers=auth(second)).json()["status"] == "REOPENED"
    assert client.post("/comments/C-1/claim", headers=auth(second)).status_code == 409
    target_id = client.get("/auth/me", headers=auth(second)).json()["id"]
    assigned = client.post("/supervisor/comments/C-1/reassign", headers=auth(supervisor), json={"reviewer_id": target_id, "reason": "Fresh review"})
    assert assigned.status_code == 200
    new = client.post("/comments/C-1/reviews", headers=auth(second), json={"result": "NO_ESCALATION", "reason": "New context reviewed"})
    assert new.status_code == 201
    history = client.get("/comments/C-1/history", headers=auth(moderator)).json()
    assert [event["event_type"] for event in history["events"]] == ["assigned", "classified", "reopen_requested", "reopen_approved", "reassigned", "classified"]
    with db.connect() as connection:
        assert connection.execute("SELECT count(*) FROM reviews WHERE comment_id='C-1'").fetchone()[0] == 2
        assert connection.execute("SELECT id FROM reviews WHERE comment_id='C-1' ORDER BY created_at, rowid").fetchone()[0] == old["review_id"]
        assert TEXT not in repr([tuple(row) for row in connection.execute("SELECT * FROM audit_events")])


def test_reject_restores_previous_closed_state_and_preserves_request(scenario):
    client, db, moderator, supervisor, _ = scenario
    review(client, moderator, "C-1", "NO_ESCALATION")
    request_id = client.post("/comments/C-1/reopen-requests", headers=auth(moderator), json={"reason": "Need second look"}).json()["request_id"]
    reject = f"/supervisor/reopen-requests/{request_id}/reject"
    assert client.post(reject, headers=auth(supervisor), json={"reason": "Existing review adequate"}).status_code == 200
    assert client.post(reject, headers=auth(supervisor), json={"reason": "Again"}).status_code == 409
    result = client.get("/comments/C-1/reopen-requests", headers=auth(moderator)).json()[0]
    assert result["status"] == "REJECTED" and result["decided_by"] is not None
    assert client.get("/comments/C-1/history", headers=auth(moderator)).json()["status"] == "CLASSIFIED"
    assert client.post("/comments/C-1/claim", headers=auth(moderator)).status_code == 409
    with db.connect() as connection:
        assert connection.execute("SELECT count(*) FROM reviews WHERE comment_id='C-1'").fetchone()[0] == 1


def test_information_request_keeps_case_closed_until_original_requester_replies(scenario):
    client, db, moderator, supervisor, second = scenario
    review(client, moderator, "C-1", "NO_ESCALATION")
    request_id = client.post("/comments/C-1/reopen-requests", headers=auth(moderator), json={"reason": "Need context"}).json()["request_id"]
    url = f"/supervisor/reopen-requests/{request_id}/request-info"
    assert client.post(url, headers=auth(supervisor), json={"reason": "Please clarify the concern"}).status_code == 200
    approve = f"/supervisor/reopen-requests/{request_id}/approve"
    assert client.post(approve, headers=auth(supervisor), json={"reason": "Too early"}).status_code == 409
    assert client.post("/comments/C-1/claim", headers=auth(second)).status_code == 409
    info = f"/comments/C-1/reopen-requests/{request_id}/information"
    assert client.post(info, headers=auth(second), json={"note": "Other person's note"}).status_code == 403
    assert client.post(info, headers=auth(moderator), json={"note": "Clarification from requester"}).status_code == 200
    listed = client.get("/supervisor/reopen-requests?status=PENDING", headers=auth(supervisor)).json()
    assert len(listed) == 1 and listed[0]["request_id"] == request_id
    assert [update["note"] for update in listed[0]["updates"]] == ["Please clarify the concern", "Clarification from requester"]
    assert client.post(approve, headers=auth(supervisor), json={"reason": "Clarified"}).status_code == 200
    with db.connect() as connection:
        assert TEXT not in repr([tuple(row) for row in connection.execute("SELECT * FROM audit_events")])


def test_bad_states_and_input_do_not_create_supervisor_actions(scenario):
    client, db, moderator, supervisor, _ = scenario
    assert client.post("/comments/missing/reopen-requests", headers=auth(moderator), json={"reason": "Missing"}).status_code == 404
    assert client.post("/comments/C-1/reopen-requests", headers=auth(moderator), json={"reason": "Pending"}).status_code == 409
    assert client.post("/supervisor/comments/C-1/resolve", headers=auth(supervisor), json={"reason": "Wrong state"}).status_code == 409
    review(client, moderator, "C-1", "ESCALATE_TO_SUPERVISOR")
    assert client.post("/supervisor/comments/C-1/resolve", headers=auth(supervisor), json={"reason": "   "}).status_code == 422
    assert client.post("/supervisor/comments/C-1/reassign", headers=auth(supervisor), json={"reviewer_id": "missing", "reason": "Target"}).status_code == 404
    with db.connect() as connection:
        assert connection.execute("SELECT count(*) FROM supervisor_actions").fetchone()[0] == 0


def test_concurrent_request_decisions_have_one_winner(scenario):
    client, db, moderator, supervisor, _ = scenario
    review(client, moderator, "C-1", "NO_ESCALATION")
    request_id = client.post("/comments/C-1/reopen-requests", headers=auth(moderator), json={"reason": "Double check"}).json()["request_id"]
    barrier = Barrier(2)

    def decide(test_client, action):
        barrier.wait(timeout=5)
        return test_client.post(f"/supervisor/reopen-requests/{request_id}/{action}", headers=auth(supervisor), json={"reason": "Decision"}).status_code

    with TestClient(create_app()) as other_client:
        with ThreadPoolExecutor(max_workers=2) as pool:
            results = [pool.submit(decide, test_client, action) for test_client, action in ((client, "approve"), (other_client, "reject"))]
            assert sorted(item.result(timeout=10) for item in results) == [200, 409]
    with db.connect() as connection:
        assert connection.execute("SELECT count(*) FROM audit_events WHERE event_type IN ('reopen_approved', 'reopen_rejected')").fetchone()[0] == 1

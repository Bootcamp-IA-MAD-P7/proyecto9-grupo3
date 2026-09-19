"""Public review contracts against a real, isolated SQLite database."""

import hashlib
import sqlite3
import time
from contextlib import contextmanager
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier, Event

import pytest
from fastapi.testclient import TestClient

from app.database import Database
from app.main import create_app
from app.auth.security import new_token


PASSWORD = "Synthetic-review-password-42!"
SENSITIVE_TEXT = "Synthetic comment text, never an audit payload."


def _headers(token):
    return {"Authorization": f"Bearer {token}"}


def _login(client, username="moderator"):
    response = client.post("/auth/login", json={"username": username, "password": PASSWORD})
    assert response.status_code == 200
    return response.json()["access_token"]


def _insert_comment(database, comment_id, score, order, text=SENSITIVE_TEXT):
    with database.connect() as connection:
        connection.execute(
            """INSERT INTO comments
               (id, video_id, text, risk_score, model_version, source_order, status)
               VALUES (?, ?, ?, ?, 'demo-simulated-v1', ?, 'PENDING')""",
            (comment_id, "V-DEMO", text, score, order),
        )


@pytest.fixture
def review_client(monkeypatch, tmp_path):
    from app.seed_demo_users import seed_demo_users
    from pwdlib import PasswordHash

    monkeypatch.setenv("MODERATION_DATABASE_PATH", str(tmp_path / "moderation.db"))
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
        _insert_comment(database, "C-1", 0.9, 1)
        _insert_comment(database, "C-2", 0.8, 2)
        _insert_comment(database, "C-3", 0.8, 3)
        _insert_comment(database, "C-4", 0.2, 4)
        yield client, database


def test_fresh_database_has_review_tables_and_version_two(tmp_path):
    database = Database(tmp_path / "new.db")
    database.initialize()
    database.initialize()
    with database.connect() as connection:
        assert connection.execute("PRAGMA user_version").fetchone()[0] == 5
        tables = {row[0] for row in connection.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        assert {"users", "sessions", "comments", "assignments", "reviews", "audit_events"} <= tables


def test_version_one_migration_keeps_user_and_live_session(monkeypatch, tmp_path):
    path = tmp_path / "legacy.db"
    token = new_token()
    with sqlite3.connect(path) as connection:
        connection.executescript("""
            CREATE TABLE users (
                id TEXT PRIMARY KEY, username TEXT UNIQUE, display_name TEXT,
                password_hash TEXT, role TEXT, is_active INTEGER, created_at INTEGER
            );
            CREATE TABLE sessions (
                token_hash TEXT PRIMARY KEY, user_id TEXT, created_at INTEGER,
                expires_at INTEGER
            );
            CREATE TABLE login_attempts (
                username TEXT PRIMARY KEY, attempts INTEGER, window_started_at INTEGER
            );
            PRAGMA user_version=1;
        """)
        connection.execute(
            "INSERT INTO users VALUES ('legacy-id', 'legacy', 'Legacy Moderator', 'stored-hash', 'MODERATOR', 1, 1)"
        )
        connection.execute(
            "INSERT INTO sessions VALUES (?, 'legacy-id', 1, ?)",
            (hashlib.sha256(token.encode()).hexdigest(), int(time.time()) + 3600),
        )
    monkeypatch.setenv("MODERATION_DATABASE_PATH", str(path))
    with TestClient(create_app()) as client:
        response = client.get("/auth/me", headers=_headers(token))
        assert response.status_code == 200
        assert response.json()["username"] == "legacy"
        with client.app.state.database.connect() as connection:
            assert connection.execute("PRAGMA user_version").fetchone()[0] == 5
            assert connection.execute("SELECT count(*) FROM comments").fetchone()[0] == 0


def test_unsupported_future_schema_does_not_change_data(tmp_path):
    path = tmp_path / "future.db"
    with sqlite3.connect(path) as connection:
        connection.execute("CREATE TABLE sentinel(value TEXT)")
        connection.execute("INSERT INTO sentinel VALUES ('keep')")
        connection.execute("PRAGMA user_version=99")
    with pytest.raises(RuntimeError):
        Database(path).initialize()
    with sqlite3.connect(path) as connection:
        assert connection.execute("SELECT value FROM sentinel").fetchone()[0] == "keep"
        assert connection.execute("PRAGMA user_version").fetchone()[0] == 99


def test_pending_queue_is_sorted_stably_and_never_contains_text(review_client):
    client, _ = review_client
    assert client.get("/comments").status_code == 401
    token = _login(client)
    response = client.get("/comments", headers=_headers(token))
    assert response.status_code == 200
    assert [item["comment_id"] for item in response.json()["items"]] == ["C-1", "C-2", "C-3", "C-4"]
    assert all("text" not in item for item in response.json()["items"])
    assert SENSITIVE_TEXT not in response.text
    assert response.headers["cache-control"] == "no-store"
    empty = client.get("/comments/status?status=CLASSIFIED", headers=_headers(token))
    assert empty.status_code == 200 and empty.json() == []


def test_two_moderators_cannot_claim_same_comment(review_client):
    client, database = review_client
    first = _login(client)
    second = _login(client, "second")
    barrier = Barrier(2)

    def claim(test_client, token):
        barrier.wait(timeout=5)
        return test_client.post("/comments/C-1/claim", headers=_headers(token)).status_code

    with TestClient(create_app()) as second_app:
        with ThreadPoolExecutor(max_workers=2) as pool:
            futures = [pool.submit(claim, test_client, token) for test_client, token in
                       ((client, first), (second_app, second))]
            assert sorted(f.result(timeout=10) for f in futures) == [200, 409]
    with database.connect() as connection:
        assert connection.execute("SELECT count(*) FROM assignments WHERE closed_at IS NULL").fetchone()[0] == 1
        assert connection.execute("SELECT count(*) FROM audit_events WHERE event_type='assigned'").fetchone()[0] == 1
    assert client.post("/comments/C-1/claim", headers=_headers(first)).status_code == 409
    assert client.post("/comments/missing/claim", headers=_headers(first)).status_code == 404


def test_expired_claim_returns_to_queue_and_old_owner_cannot_decide(review_client):
    client, database = review_client
    first = _login(client)
    second = _login(client, "second")
    claim = client.post("/comments/C-1/claim", headers=_headers(first))
    assert claim.status_code == 200
    assert claim.json()["status"] == "IN_REVIEW"
    assert claim.json()["claim_expires_at"] > int(time.time())
    with database.connect() as connection:
        connection.execute("UPDATE assignments SET claimed_at=0, expires_at=1 WHERE comment_id='C-1'")
    pending = client.get("/comments", headers=_headers(second)).json()["items"]
    assert "C-1" in [item["comment_id"] for item in pending]
    stale = client.post(
        "/comments/C-1/reviews", headers=_headers(first),
        json={"result": "NO_ESCALATION", "reason": "A reviewed decision"},
    )
    assert stale.status_code == 409
    assert client.post("/comments/C-1/claim", headers=_headers(second)).status_code == 200
    with database.connect() as connection:
        assert connection.execute("SELECT count(*) FROM audit_events WHERE event_type='claim_expired'").fetchone()[0] == 1


@pytest.mark.parametrize("operation", ["claim", "reveal", "review"])
def test_lease_is_checked_after_waiting_for_sqlite_lock(review_client, monkeypatch, operation):
    from app.comments.repository import CommentConflict, NotAssignee
    from app.comments.schemas import ReviewRequest

    client, database = review_client
    owner_token = _login(client)
    other_token = _login(client, "second")
    service = client.app.state.comment_service
    owner = client.app.state.auth_service.authenticate(owner_token)
    other = client.app.state.auth_service.authenticate(other_token)
    assert client.post("/comments/C-1/claim", headers=_headers(owner_token)).status_code == 200
    with database.connect() as connection:
        connection.execute(
            "UPDATE assignments SET claimed_at=0, expires_at=200 WHERE comment_id='C-1'"
        )

    clock = [199]
    monkeypatch.setattr(service.repository, "_now", lambda: clock[0])
    entered_connection = Event()
    original_connect = database.connect

    @contextmanager
    def signaled_connect():
        with original_connect() as connection:
            entered_connection.set()
            yield connection

    monkeypatch.setattr(database, "connect", signaled_connect)

    def attempt():
        if operation == "claim":
            return service.claim("C-1", other)
        if operation == "reveal":
            return service.reveal("C-1", owner)
        return service.review(
            "C-1", owner,
            ReviewRequest(result="NO_ESCALATION", reason="Too late"),
        )

    writer = sqlite3.connect(database.path, timeout=5)
    try:
        writer.execute("BEGIN IMMEDIATE")
        with ThreadPoolExecutor(max_workers=1) as pool:
            future = pool.submit(attempt)
            assert entered_connection.wait(timeout=2)
            clock[0] = 201
            writer.commit()
            if operation == "claim":
                assert future.result(timeout=5)["status"] == "IN_REVIEW"
            else:
                with pytest.raises(NotAssignee if operation == "reveal" else CommentConflict):
                    future.result(timeout=5)
    finally:
        writer.rollback()
        writer.close()


def test_only_current_owner_can_reveal_and_audit_never_copies_text(review_client, caplog):
    client, database = review_client
    first = _login(client)
    second = _login(client, "second")
    assert client.get("/comments/C-1/content").status_code == 401
    assert client.get("/comments/missing/content", headers=_headers(first)).status_code == 404
    assert client.get("/comments/C-1/content", headers=_headers(first)).status_code == 403
    assert client.post("/comments/C-1/claim", headers=_headers(first)).status_code == 200
    denied = client.get("/comments/C-1/content", headers=_headers(second))
    assert denied.status_code == 403 and SENSITIVE_TEXT not in denied.text
    revealed = client.get("/comments/C-1/content", headers=_headers(first))
    assert revealed.status_code == 200
    assert revealed.json() == {"comment_id": "C-1", "text": SENSITIVE_TEXT}
    assert revealed.headers["cache-control"] == "no-store"
    with database.connect() as connection:
        assert connection.execute("SELECT count(*) FROM audit_events WHERE event_type='content_revealed'").fetchone()[0] == 1
        assert SENSITIVE_TEXT not in repr([tuple(row) for row in connection.execute("SELECT * FROM audit_events")])
    assert SENSITIVE_TEXT not in caplog.text


@pytest.mark.parametrize(
    "result,status,event",
    [
        ("NO_ESCALATION", "CLASSIFIED", "classified"),
        ("ESCALATE_TO_SUPERVISOR", "ESCALATED", "escalated"),
        ("INSUFFICIENT_CONTEXT", "ESCALATED", "escalated"),
        ("TRANSFER_REQUESTED", "ESCALATED", "escalated"),
    ],
)
def test_decision_is_attributed_saved_and_removed_from_pending(review_client, result, status, event):
    client, database = review_client
    token = _login(client)
    assert client.post("/comments/C-1/claim", headers=_headers(token)).status_code == 200
    response = client.post(
        "/comments/C-1/reviews", headers=_headers(token),
        json={"result": result, "reason": "Human review of the synthetic example"},
    )
    assert response.status_code == 201
    body = response.json()
    assert body["result"] == result and body["status"] == status
    assert body["reviewer_display_name"] == "Demo Moderator"
    assert body["model_score"] == 0.9
    assert body["model_version"] == "demo-simulated-v1"
    assert "C-1" not in [item["comment_id"] for item in client.get("/comments", headers=_headers(token)).json()["items"]]
    assert client.post("/comments/C-1/claim", headers=_headers(token)).status_code == 409
    assert client.post(
        "/comments/C-1/reviews", headers=_headers(token),
        json={"result": result, "reason": "Duplicate"},
    ).status_code == 409
    with database.connect() as connection:
        assert connection.execute("SELECT count(*) FROM reviews WHERE comment_id='C-1'").fetchone()[0] == 1
        assert connection.execute("SELECT count(*) FROM audit_events WHERE event_type=?", (event,)).fetchone()[0] == 1


def test_nonowner_invalid_reason_and_invalid_result_do_not_create_reviews(review_client):
    client, database = review_client
    first = _login(client)
    second = _login(client, "second")
    assert client.post("/comments/C-1/claim", headers=_headers(first)).status_code == 200
    payload = {"result": "NO_ESCALATION", "reason": "Human decision"}
    assert client.post("/comments/C-1/reviews", headers=_headers(second), json=payload).status_code == 403
    assert client.post("/comments/C-1/reviews", headers=_headers(first), json={**payload, "reason": "   "}).status_code == 422
    assert client.post("/comments/C-1/reviews", headers=_headers(first), json={**payload, "result": "DELETE_USER"}).status_code == 422
    with database.connect() as connection:
        assert connection.execute("SELECT count(*) FROM reviews").fetchone()[0] == 0


def test_history_shows_attribution_and_reason_without_comment_text(review_client):
    client, database = review_client
    first = _login(client)
    second = _login(client, "second")
    assert client.get("/comments/C-1/history").status_code == 401
    assert client.get("/comments/missing/history", headers=_headers(first)).status_code == 404
    client.post("/comments/C-1/claim", headers=_headers(first))
    client.get("/comments/C-1/content", headers=_headers(first))
    client.post(
        "/comments/C-1/reviews", headers=_headers(first),
        json={"result": "NO_ESCALATION", "reason": "No further action after manual review"},
    )
    history = client.get("/comments/C-1/history", headers=_headers(second))
    assert history.status_code == 200
    assert history.headers["cache-control"] == "no-store"
    assert [event["event_type"] for event in history.json()["events"]] == [
        "assigned", "content_revealed", "classified",
    ]
    decision = history.json()["events"][-1]
    assert decision["actor_display_name"] == "Demo Moderator"
    assert decision["result"] == "NO_ESCALATION"
    assert decision["reason"] == "No further action after manual review"
    assert decision["model_score"] == 0.9
    assert SENSITIVE_TEXT not in history.text
    with database.connect() as connection:
        assert SENSITIVE_TEXT not in repr([tuple(row) for row in connection.execute("SELECT * FROM audit_events")])


def test_synthetic_seed_is_explicit_idempotent_and_preserves_decisions(review_client):
    from app.seed_demo_comments import seed_demo_comments

    client, database = review_client
    assert seed_demo_comments(database) == 3
    assert seed_demo_comments(database) == 0
    with database.connect() as connection:
        rows = connection.execute(
            "SELECT id, model_version FROM comments WHERE id LIKE 'C-DEMO-%' ORDER BY id"
        ).fetchall()
    assert len(rows) == 3
    assert all(row["model_version"] == "demo-simulated-v1" for row in rows)
    token = _login(client)
    assert client.post("/comments/C-DEMO-001/claim", headers=_headers(token)).status_code == 200
    assert client.post(
        "/comments/C-DEMO-001/reviews", headers=_headers(token),
        json={"result": "NO_ESCALATION", "reason": "Synthetic example reviewed"},
    ).status_code == 201
    assert seed_demo_comments(database) == 0
    with database.connect() as connection:
        assert connection.execute("SELECT status FROM comments WHERE id='C-DEMO-001'").fetchone()[0] == "CLASSIFIED"
        assert connection.execute("SELECT count(*) FROM reviews WHERE comment_id='C-DEMO-001'").fetchone()[0] == 1

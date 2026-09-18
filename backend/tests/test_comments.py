"""Comment ingestion and prioritized queue behavior through real HTTP and SQLite."""

import pytest
from fastapi.testclient import TestClient

from app.database import Database
from app.main import create_app
from app.seed_demo_users import seed_demo_users


PASSWORD = "Synthetic-test-password-42!"


@pytest.fixture
def client():
    with TestClient(create_app()) as current:
        seed_demo_users(current.app.state.database, PASSWORD, PASSWORD)
        yield current


def headers(client, username="supervisor"):
    response = client.post("/auth/login", json={"username": username, "password": PASSWORD})
    assert response.status_code == 200
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def item(comment_id, text="Synthetic example", video_id="video-1"):
    return {"comment_id": comment_id, "video_id": video_id, "text": text}


def test_supervisor_imports_and_both_roles_see_text_free_queue(client):
    supervisor = headers(client)
    moderator = headers(client, "moderator")
    payload = {"items": [item("c1", "Private synthetic text"), item("c2", "Another synthetic text")]}
    assert client.post("/comments/import", json=payload).status_code == 401
    assert client.post("/comments/import", json=payload, headers=moderator).status_code == 403
    created = client.post("/comments/import", json=payload, headers=supervisor)
    assert created.status_code == 201
    assert created.json() == {"imported": 2}
    response = client.get("/comments", headers=moderator)
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 2
    assert {row["comment_id"] for row in data["items"]} == {"c1", "c2"}
    assert all(set(row) == {"comment_id", "video_id", "risk_score", "uncertainty", "model_version", "score_source", "status"} for row in data["items"])
    assert all(row["status"] == "PENDING" and row["score_source"] == "SIMULATED" for row in data["items"])
    assert "Private synthetic text" not in response.text
    assert response.headers["cache-control"] == "no-store"


def test_queue_orders_by_score_then_input_order_and_paginates(client):
    class Scorer:
        def score_comment(self, text):
            from app.comments.scoring import Score
            return Score({"low": 0.1, "high-one": 0.9, "high-two": 0.9}[text], 1.0, "test-simulated", "SIMULATED")

    client.app.state.comment_service.scorer = Scorer()
    h = headers(client)
    body = {"items": [item("low", "low"), item("a", "high-one"), item("b", "high-two")]}
    assert client.post("/comments/import", json=body, headers=h).status_code == 201
    first = client.get("/comments", params={"page": 1, "page_size": 2}, headers=h).json()
    second = client.get("/comments", params={"page": 2, "page_size": 2}, headers=h).json()
    assert [row["comment_id"] for row in first["items"]] == ["a", "b"]
    assert [row["comment_id"] for row in second["items"]] == ["low"]
    assert first["has_next"] is True and second["has_next"] is False
    assert first["total"] == second["total"] == 3
    assert client.get("/comments", params={"page": 0}, headers=h).status_code == 422
    assert client.get("/comments", params={"page_size": 101}, headers=h).status_code == 422


@pytest.mark.parametrize("body", [
    {"items": []},
    {"items": [item("x", "   ")]},
    {"items": [item("x"), item("x")]},
    {"items": [dict(item("x"), IsToxic=1)]},
])
def test_invalid_import_has_no_partial_writes_or_echoed_text(client, body):
    h = headers(client)
    response = client.post("/comments/import", json=body, headers=h)
    assert response.status_code == 422
    assert client.get("/comments", headers=h).json()["total"] == 0
    assert "Synthetic example" not in response.text


def test_existing_duplicate_rejects_entire_batch(client):
    h = headers(client)
    assert client.post("/comments/import", json={"items": [item("existing")]}, headers=h).status_code == 201
    response = client.post("/comments/import", json={"items": [item("new"), item("existing")]}, headers=h)
    assert response.status_code == 409
    assert client.get("/comments", headers=h).json()["total"] == 1


def test_queue_count_matches_visible_scored_rows(client):
    with client.app.state.database.connect() as connection:
        connection.execute("INSERT INTO comments(comment_id,video_id,text) VALUES (?,?,?)",
                           ("unscored", "v1", "Synthetic unscored comment"))
    response = client.get("/comments", headers=headers(client))
    assert response.status_code == 200
    assert response.json()["items"] == []
    assert response.json()["total"] == 0


def test_scoring_failure_does_not_write_or_return_empty_success(client):
    class BrokenScorer:
        def score_comment(self, text):
            raise RuntimeError("model unavailable")

    client.app.state.comment_service.scorer = BrokenScorer()
    h = headers(client)
    response = client.post("/comments/import", json={"items": [item("c1")]}, headers=h)
    assert response.status_code == 503
    assert client.get("/comments", headers=h).json()["total"] == 0


def test_version_two_migration_preserves_users_sessions_and_comments(tmp_path):
    path = tmp_path / "old.db"
    db = Database(path)
    with db.connect() as connection:
        db._create_persistence_schema(connection)
        db._create_auth_schema(connection)
        connection.execute("PRAGMA user_version=2")
        connection.execute("INSERT INTO users(id,username,display_name,password_hash,role,created_at) VALUES (?,?,?,?,?,?)",
                           ("u1", "legacy", "Legacy User", "synthetic-hash", "MODERATOR", 1))
        user_count = connection.execute("SELECT count(*) FROM users").fetchone()[0]
        user_id = connection.execute("SELECT id FROM users LIMIT 1").fetchone()[0]
        connection.execute("INSERT INTO sessions(token_hash,user_id,created_at,expires_at) VALUES (?,?,?,?)",
                           ("a" * 64, user_id, 1, 9999999999))
        connection.execute("INSERT INTO comments(comment_id,video_id,text) VALUES (?,?,?)",
                           ("legacy", "v1", "Synthetic existing comment"))
    db.initialize()
    with db.connect() as connection:
        assert connection.execute("PRAGMA user_version").fetchone()[0] == 3
        assert connection.execute("SELECT count(*) FROM users").fetchone()[0] == user_count
        assert connection.execute("SELECT count(*) FROM sessions").fetchone()[0] == 1
        row = connection.execute("SELECT comment_id,risk_score,model_version,score_source FROM comments").fetchone()
        assert row["comment_id"] == "legacy"
        assert 0 <= row["risk_score"] <= 1
        assert (row["model_version"], row["score_source"]) == ("simulated-v1", "SIMULATED")

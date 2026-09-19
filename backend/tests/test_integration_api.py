"""A synthetic end-to-end import, claim and review path."""

from fastapi.testclient import TestClient

from app.main import create_app
from app.seed_demo_users import seed_demo_users


def test_import_queue_review_and_history(monkeypatch, tmp_path):
    monkeypatch.setenv("MODERATION_DATABASE_PATH", str(tmp_path / "integration.db"))
    with TestClient(create_app()) as client:
        seed_demo_users(client.app.state.database, "Synthetic-password-42!", "Synthetic-password-42!")
        login = client.post("/auth/login", json={
            "username": "supervisor", "password": "Synthetic-password-42!",
        })
        assert login.status_code == 200
        headers = {"Authorization": f"Bearer {login.json()['access_token']}"}
        imported = client.post("/comments/import", headers=headers, json={"items": [
            {"comment_id": "A", "video_id": "V", "text": "synthetic one"},
            {"comment_id": "B", "video_id": "V", "text": "synthetic two"},
        ]})
        assert imported.status_code == 201
        assert imported.json() == {"imported": 2}
        queue = client.get("/comments/queue?page_size=1", headers=headers)
        assert queue.status_code == 200
        assert queue.json()["total"] == 2
        assert queue.json()["has_next"] is True
        assert "text" not in queue.text
        comment_id = queue.json()["items"][0]["comment_id"]
        assert client.post(f"/comments/{comment_id}/claim", headers=headers).status_code == 200
        assigned = client.get("/comments/assigned", headers=headers)
        assert assigned.status_code == 200
        assert comment_id in [item["comment_id"] for item in assigned.json()]
        assert "text" not in assigned.text
        assert client.get(f"/comments/{comment_id}/content", headers=headers).status_code == 200
        assert client.post(f"/comments/{comment_id}/reviews", headers=headers, json={
            "result": "NO_ESCALATION", "reason": "Synthetic reviewed example",
        }).status_code == 201
        history = client.get(f"/comments/{comment_id}/history", headers=headers)
        assert history.status_code == 200
        assert history.json()["status"] == "CLASSIFIED"


def test_import_is_supervisor_only_and_duplicate_batch_is_atomic(monkeypatch, tmp_path):
    monkeypatch.setenv("MODERATION_DATABASE_PATH", str(tmp_path / "atomic.db"))
    with TestClient(create_app()) as client:
        seed_demo_users(client.app.state.database, "Synthetic-password-42!", "Synthetic-password-42!")
        def headers(username):
            token = client.post("/auth/login", json={
                "username": username, "password": "Synthetic-password-42!",
            }).json()["access_token"]
            return {"Authorization": f"Bearer {token}"}
        moderator = headers("moderator")
        supervisor = headers("supervisor")
        item = {"comment_id": "A", "video_id": "V", "text": "synthetic text"}
        assert client.post("/comments/import", headers=moderator,
                           json={"items": [item]}).status_code == 403
        assert client.post("/comments/import", headers=supervisor,
                           json={"items": [item]}).status_code == 201
        duplicate = client.post("/comments/import", headers=supervisor,
                                json={"items": [{**item, "comment_id": "B"}, item]})
        assert duplicate.status_code == 409
        assert client.get("/comments/queue", headers=moderator).json()["total"] == 1


def test_scoring_failure_writes_no_partial_batch(monkeypatch, tmp_path):
    monkeypatch.setenv("MODERATION_DATABASE_PATH", str(tmp_path / "scoring.db"))
    with TestClient(create_app()) as client:
        seed_demo_users(client.app.state.database, "Synthetic-password-42!", "Synthetic-password-42!")
        token = client.post("/auth/login", json={
            "username": "supervisor", "password": "Synthetic-password-42!",
        }).json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}
        service = client.app.state.comment_service
        original_scorer = service.scorer
        class FailingScorer:
            def score_comment(self, text):
                if text == "fail":
                    raise RuntimeError("synthetic failure")
                return original_scorer.score_comment(text)
        service.scorer = FailingScorer()
        response = client.post("/comments/import", headers=headers, json={"items": [
            {"comment_id": "A", "video_id": "V", "text": "first"},
            {"comment_id": "B", "video_id": "V", "text": "fail"},
        ]})
        assert response.status_code == 503
        assert client.get("/comments/queue", headers=headers).json()["total"] == 0

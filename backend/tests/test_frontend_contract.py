from fastapi.testclient import TestClient

from app.main import create_app


def test_frontend_assets_are_served_without_credentials(monkeypatch, tmp_path):
    monkeypatch.setenv("MODERATION_DATABASE_PATH", str(tmp_path / "ui.db"))
    with TestClient(create_app()) as client:
        page = client.get("/ui/")
        assert page.status_code == 200
        assert "Moderación" in page.text
        assert client.get("/ui/app.js").status_code == 200
        assert client.get("/ui/styles.css").status_code == 200

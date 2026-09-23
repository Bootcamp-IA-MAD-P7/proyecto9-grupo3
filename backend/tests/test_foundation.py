"""Exercise the public HTTP contract and environment-driven app construction."""

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError


@pytest.fixture(autouse=True)
def isolated_environment(monkeypatch, tmp_path):
    """Do not let a developer's .env or shell change the test inputs."""
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("MODERATION_APP_NAME", raising=False)
    monkeypatch.delenv("MODERATION_DOCS_ENABLED", raising=False)


def test_health_is_public_and_only_reports_process_liveness():
    from app.main import create_app

    with TestClient(create_app()) as client:
        response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_openapi_describes_the_health_response():
    from app.main import create_app

    with TestClient(create_app()) as client:
        response = client.get("/openapi.json")

    assert response.status_code == 200
    schema = response.json()
    health_schema = schema["paths"]["/health"]["get"]["responses"]["200"][
        "content"
    ]["application/json"]["schema"]
    model_name = health_schema["$ref"].rsplit("/", 1)[-1]
    assert schema["components"]["schemas"][model_name]["properties"]["status"][
        "const"
    ] == "ok"


def test_interactive_docs_are_available_for_local_learning():
    from app.main import create_app

    with TestClient(create_app()) as client:
        response = client.get("/docs")

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/html")


@pytest.mark.parametrize("path", ["/docs", "/redoc", "/openapi.json"])
def test_documentation_can_be_disabled_without_disabling_health(monkeypatch, path):
    from app.main import create_app

    monkeypatch.setenv("MODERATION_DOCS_ENABLED", "false")
    with TestClient(create_app()) as client:
        assert client.get(path).status_code == 404
        assert client.get("/health").status_code == 200


def test_app_title_uses_environment_configuration(monkeypatch):
    from app.main import create_app

    monkeypatch.setenv("MODERATION_APP_NAME", "Teaching API")
    with TestClient(create_app()) as client:
        assert client.get("/openapi.json").json()["info"]["title"] == "Teaching API"


@pytest.mark.parametrize("name", ["DATABASE_URL", "MODERATION_DATABASE_URL"])
def test_postgres_url_uses_neon_compatible_environment_names(monkeypatch, name):
    from app.main import create_app

    url = "postgresql://user:secret@example.neon.tech/moderation?sslmode=require"
    monkeypatch.setenv(name, url)
    app = create_app()
    assert app.state.database.is_postgres is True
    assert app.state.database.url == url


def test_invalid_configuration_fails_before_serving_requests(monkeypatch):
    from app.main import create_app

    monkeypatch.setenv("MODERATION_DOCS_ENABLED", "not-a-boolean")
    with pytest.raises(ValidationError):
        create_app()


def test_dotenv_is_optional_and_shell_values_take_precedence(monkeypatch, tmp_path):
    from app.main import create_app

    (tmp_path / ".env").write_text("MODERATION_APP_NAME=File API\n", encoding="utf-8")
    with TestClient(create_app()) as client:
        assert client.get("/openapi.json").json()["info"]["title"] == "File API"

    monkeypatch.setenv("MODERATION_APP_NAME", "Shell API")
    with TestClient(create_app()) as client:
        assert client.get("/openapi.json").json()["info"]["title"] == "Shell API"

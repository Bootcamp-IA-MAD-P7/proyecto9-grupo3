"""Auth contracts against real SQLite and real password hashing."""

import hashlib
import json
import sqlite3
from concurrent.futures import ThreadPoolExecutor

import pytest
from fastapi import Depends
from fastapi.testclient import TestClient
from pydantic import ValidationError

from app.main import create_app


# Synthetic, test-only credentials, never used to provision a developer database.
PASSWORD = "Synthetic-test-password-42!"


@pytest.fixture
def auth_client():
    from app.auth.dependencies import require_roles
    from app.auth.models import Role
    from app.seed_demo_users import seed_demo_users

    app = create_app()

    @app.get("/test/supervisor", dependencies=[Depends(require_roles(Role.SUPERVISOR))])
    def supervisor_only():
        return {"allowed": True}

    with TestClient(app) as client:
        seed_demo_users(app.state.database, PASSWORD, PASSWORD)
        yield client


def login(client, username="moderator"):
    response = client.post("/auth/login", json={"username": username, "password": PASSWORD})
    assert response.status_code == 200
    return response.json()


def authorization(token):
    return {"Authorization": f"Bearer {token}"}


def test_login_route_rejects_unknown_user_instead_of_being_missing():
    with TestClient(create_app()) as client:
        response = client.post("/auth/login", json={"username": "unknown", "password": PASSWORD})
    assert response.status_code == 401


@pytest.mark.parametrize("username,role", [("moderator", "MODERATOR"), ("supervisor", "SUPERVISOR")])
def test_login_and_me_return_public_user_and_expiring_token(auth_client, username, role):
    result = login(auth_client, username)
    assert result["token_type"] == "bearer"
    assert result["expires_in"] == 1800
    assert len(result["access_token"]) == 43
    assert set(result["user"]) == {"id", "username", "display_name", "role"}
    assert result["user"]["role"] == role
    response = auth_client.get("/auth/me", headers=authorization(result["access_token"]))
    assert response.status_code == 200
    assert response.json() == result["user"]
    assert response.headers["cache-control"] == "no-store"


def test_seed_hashes_are_salted_and_reseeding_preserves_credentials(auth_client):
    from pwdlib import PasswordHash
    from app.seed_demo_users import seed_demo_users

    database = auth_client.app.state.database
    with database.connect() as connection:
        before = connection.execute("SELECT username, password_hash FROM users ORDER BY username").fetchall()
    assert len(before) == 2
    hashes = [row["password_hash"] for row in before]
    assert hashes[0] != hashes[1]
    assert all(value.startswith("$argon2id$") for value in hashes)
    assert all(PasswordHash.recommended().verify(PASSWORD, value) for value in hashes)
    seed_demo_users(database, "Different-test-password-1!", "Different-test-password-2!")
    database.initialize()
    with database.connect() as connection:
        after = connection.execute("SELECT username, password_hash FROM users ORDER BY username").fetchall()
    assert [tuple(row) for row in before] == [tuple(row) for row in after]
    assert PASSWORD.encode() not in database.path.read_bytes()


def test_database_stores_token_digest_not_bearer_secret(auth_client):
    token = login(auth_client)["access_token"]
    with auth_client.app.state.database.connect() as connection:
        stored = connection.execute("SELECT token_hash FROM sessions").fetchone()[0]
    assert stored == hashlib.sha256(token.encode()).hexdigest()
    assert token.encode() not in auth_client.app.state.database.path.read_bytes()


def test_auth_migration_keeps_existing_comments_and_users(tmp_path):
    from app.database import Database

    database = Database(tmp_path / "migration.db")
    with database.connect() as connection:
        database._create_persistence_schema(connection)
        connection.execute("PRAGMA user_version=1")
        connection.execute("INSERT INTO users(id,username,display_name,password_hash,role,created_at) VALUES (?,?,?,?,?,?)",
                           ("u1", "legacy", "Legacy User", "synthetic-hash", "MODERATOR", 1))
        connection.execute("INSERT INTO comments(comment_id,video_id,text) VALUES (?,?,?)",
                           ("c1", "v1", "Synthetic existing comment"))
    database.initialize()
    with database.connect() as connection:
        assert connection.execute("PRAGMA user_version").fetchone()[0] == 3
        assert connection.execute("SELECT count(*) FROM users").fetchone()[0] == 1
        assert connection.execute("SELECT count(*) FROM comments").fetchone()[0] == 1
        assert connection.execute("SELECT count(*) FROM sessions").fetchone()[0] == 0


def test_unknown_wrong_and_inactive_credentials_have_same_response(auth_client):
    bodies = []
    for username, password in [("unknown", PASSWORD), ("moderator", "wrong")]:
        response = auth_client.post("/auth/login", json={"username": username, "password": password})
        assert response.status_code == 401
        bodies.append(response.json())
    with auth_client.app.state.database.connect() as connection:
        connection.execute("UPDATE users SET is_active=0 WHERE username='supervisor'")
    response = auth_client.post("/auth/login", json={"username": "supervisor", "password": PASSWORD})
    assert response.status_code == 401
    assert bodies[0] == bodies[1] == response.json()
    assert response.headers["www-authenticate"] == "Bearer"
    with auth_client.app.state.database.connect() as connection:
        assert connection.execute("SELECT count(*) FROM sessions").fetchone()[0] == 0


@pytest.mark.parametrize("header", [None, "Basic abc", "Bearer invalid", "Bearer " + "a" * 43, "Bearer " + "a" * 1000])
def test_missing_malformed_and_unknown_tokens_return_401(auth_client, header):
    response = auth_client.get("/auth/me", headers={} if header is None else {"Authorization": header})
    assert response.status_code == 401
    assert response.headers["www-authenticate"] == "Bearer"


def test_token_in_query_is_not_authentication(auth_client):
    token = login(auth_client)["access_token"]
    assert auth_client.get("/auth/me", params={"access_token": token}).status_code == 401


def test_expired_session_is_rejected(auth_client):
    token = login(auth_client)["access_token"]
    with auth_client.app.state.database.connect() as connection:
        connection.execute("UPDATE sessions SET created_at=1, expires_at=2")
    assert auth_client.get("/auth/me", headers=authorization(token)).status_code == 401


def test_logout_revokes_only_current_session(auth_client):
    first = login(auth_client)["access_token"]
    second = login(auth_client)["access_token"]
    response = auth_client.post("/auth/logout", headers=authorization(first))
    assert response.status_code == 204
    assert response.content == b""
    assert auth_client.get("/auth/me", headers=authorization(first)).status_code == 401
    assert auth_client.get("/auth/me", headers=authorization(second)).status_code == 200


def test_session_is_shared_by_another_app_instance(auth_client):
    token = login(auth_client)["access_token"]
    with TestClient(create_app()) as other_client:
        assert other_client.get("/auth/me", headers=authorization(token)).status_code == 200
        assert other_client.post("/auth/logout", headers=authorization(token)).status_code == 204
    assert auth_client.get("/auth/me", headers=authorization(token)).status_code == 401


def test_role_guard_distinguishes_401_403_and_success(auth_client):
    assert auth_client.get("/test/supervisor").status_code == 401
    moderator = login(auth_client)["access_token"]
    forged_headers = {**authorization(moderator), "X-Role": "SUPERVISOR"}
    assert auth_client.get("/test/supervisor?role=SUPERVISOR", headers=forged_headers).status_code == 403
    supervisor = login(auth_client, "supervisor")["access_token"]
    assert auth_client.get("/test/supervisor", headers=authorization(supervisor)).json() == {"allowed": True}


def test_role_and_active_state_are_rechecked_for_existing_sessions(auth_client):
    token = login(auth_client, "supervisor")["access_token"]
    with auth_client.app.state.database.connect() as connection:
        connection.execute("UPDATE users SET role='MODERATOR' WHERE username='supervisor'")
    assert auth_client.get("/test/supervisor", headers=authorization(token)).status_code == 403
    assert auth_client.get("/auth/me", headers=authorization(token)).json()["role"] == "MODERATOR"
    with auth_client.app.state.database.connect() as connection:
        connection.execute("UPDATE users SET is_active=0 WHERE username='supervisor'")
    assert auth_client.get("/auth/me", headers=authorization(token)).status_code == 401


@pytest.mark.parametrize("body", [
    {"username": "moderator", "password": PASSWORD, "role": "SUPERVISOR"},
    {"password": PASSWORD},
    {"username": "moderator", "password": "x" * 1025},
])
def test_validation_does_not_echo_secrets(auth_client, body, caplog):
    response = auth_client.post("/auth/login", json=body)
    assert response.status_code == 422
    assert body["password"] not in response.text
    assert body["password"] not in caplog.text
    assert all("input" not in error for error in response.json()["detail"])
    assert response.headers["cache-control"] == "no-store"


def test_authentication_does_not_log_passwords_or_tokens(auth_client, caplog):
    result = login(auth_client)
    auth_client.get("/auth/me", headers=authorization(result["access_token"]))
    assert PASSWORD not in caplog.text
    assert result["access_token"] not in caplog.text


def test_validation_does_not_echo_client_controlled_field_names(auth_client):
    response = auth_client.post("/auth/login", json={
        "username": "moderator", "password": PASSWORD, PASSWORD: "extra",
    })
    assert response.status_code == 422
    assert PASSWORD not in response.text


@pytest.mark.parametrize("password", ["\ud800", "\udfff"], ids=["unpaired-high-surrogate", "unpaired-low-surrogate"])
def test_malformed_unicode_password_returns_validation_error(auth_client, password):
    response = auth_client.post(
        "/auth/login",
        content=json.dumps({"username": "moderator", "password": password}),
        headers={"Content-Type": "application/json"},
    )
    assert response.status_code == 422
    assert "input" not in response.json()["detail"][0]


def test_throttle_is_persistent_and_window_can_expire(auth_client):
    for _ in range(5):
        assert auth_client.post("/auth/login", json={"username": "moderator", "password": "bad"}).status_code == 401
    with TestClient(create_app()) as other_client:
        response = other_client.post("/auth/login", json={"username": " MODERATOR ", "password": PASSWORD})
    assert response.status_code == 429
    assert 1 <= int(response.headers["retry-after"]) <= 60
    with auth_client.app.state.database.connect() as connection:
        connection.execute("UPDATE login_attempts SET window_started_at=1")
    assert login(auth_client)["user"]["username"] == "moderator"


def test_parallel_attempts_cannot_bypass_limit(auth_client):
    def attempt(_):
        return auth_client.post("/auth/login", json={"username": "unknown", "password": "bad"}).status_code

    with ThreadPoolExecutor(max_workers=6) as executor:
        statuses = list(executor.map(attempt, range(6)))
    assert statuses.count(401) == 5
    assert statuses.count(429) == 1


def test_successful_login_clears_attempt_counter(auth_client):
    for _ in range(4):
        auth_client.post("/auth/login", json={"username": "moderator", "password": "bad"})
    login(auth_client)
    assert auth_client.post("/auth/login", json={"username": "moderator", "password": "bad"}).status_code == 401


def test_database_rejects_unknown_roles_and_orphan_sessions(auth_client):
    with pytest.raises(sqlite3.IntegrityError), auth_client.app.state.database.connect() as connection:
        connection.execute("UPDATE users SET role='ADMIN' WHERE username='moderator'")
    with pytest.raises(sqlite3.IntegrityError), auth_client.app.state.database.connect() as connection:
        connection.execute("INSERT INTO sessions VALUES (?, ?, ?, ?)", ("a" * 64, "missing", 1, 2))


def test_newer_schema_is_rejected_without_replacing_data(auth_client):
    database = auth_client.app.state.database
    with database.connect() as connection:
        connection.execute("PRAGMA user_version=999")
    with pytest.raises(RuntimeError, match="schema"):
        database.initialize()
    with database.connect() as connection:
        assert connection.execute("PRAGMA user_version").fetchone()[0] == 999
        assert connection.execute("SELECT count(*) FROM users").fetchone()[0] == 2


@pytest.mark.parametrize("password", ["short", "x" * 1025])
def test_seed_rejects_invalid_passwords_before_creating_users(tmp_path, password):
    from app.database import Database
    from app.seed_demo_users import seed_demo_users

    database = Database(tmp_path / "seed.db")
    with pytest.raises(ValueError, match="12"):
        seed_demo_users(database, password, PASSWORD)


@pytest.mark.parametrize("setting,value", [
    ("MODERATION_SESSION_TTL_SECONDS", "0"),
    ("MODERATION_LOGIN_MAX_ATTEMPTS", "0"),
    ("MODERATION_LOGIN_WINDOW_SECONDS", "0"),
])
def test_invalid_auth_settings_prevent_app_creation(monkeypatch, setting, value):
    monkeypatch.setenv(setting, value)
    with pytest.raises(ValidationError):
        create_app()


def test_openapi_marks_protected_routes_and_has_no_registration(auth_client):
    paths = auth_client.get("/openapi.json").json()["paths"]
    assert paths["/auth/me"]["get"]["security"]
    assert paths["/auth/logout"]["post"]["security"]
    assert not paths["/auth/login"]["post"].get("security")
    assert "/auth/register" not in paths

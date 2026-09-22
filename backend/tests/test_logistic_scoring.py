"""Inference contract tests using a small synthetic, fitted artifact."""

import hashlib
import json

import joblib
import pytest
from sklearn.pipeline import Pipeline

from app.comments.scoring import LogisticScorer, ModelArtifactUnavailable
from app.main import create_app
from app.seed_demo_users import seed_demo_users
from src.moderation.models.logistic_tfidf import build_pipeline
from fastapi.testclient import TestClient


@pytest.fixture
def artifact(tmp_path):
    model = build_pipeline()
    model.set_params(tfidf__min_df=1)
    model.fit(
        ["kind helpful person", "welcome friend", "awful hateful insult", "bad rude abuse"],
        [0, 0, 1, 1],
    )
    path = tmp_path / "logistic_tfidf.joblib"
    joblib.dump(model, path)
    metadata = path.with_name("artifact_metadata.json")
    metadata.write_text(json.dumps({
        "model_version": "logistic-tfidf-v1",
        "artifact_sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
    }), encoding="utf-8")
    return path, metadata


def test_loads_artifact_once_and_scores_reproducibly(artifact, monkeypatch):
    path, metadata = artifact
    scorer = LogisticScorer(path, metadata)
    first = scorer.score_comment("kind helpful person")
    second = scorer.score_comment("kind helpful person")
    assert first == second
    assert 0 <= first.risk_score <= 1
    assert 0 <= first.uncertainty <= 1
    assert first.model_version == "logistic-tfidf-v1"
    assert first.score_source == "MODEL"

    def fail(*args, **kwargs):
        raise AssertionError("inference must not train")

    monkeypatch.setattr(Pipeline, "fit", fail)
    assert scorer.score_comment("potentially hateful abuse").score_source == "MODEL"


def test_neutral_and_toxic_synthetic_text_are_scored(artifact):
    scorer = LogisticScorer(*artifact)
    neutral = scorer.score_comment("kind helpful person")
    toxic = scorer.score_comment("awful hateful insult")
    assert neutral.risk_score < toxic.risk_score


def test_rejects_empty_text(artifact):
    with pytest.raises(ValueError, match="must not be empty"):
        LogisticScorer(*artifact).score_comment("  ")


def test_missing_artifact_is_controlled(tmp_path):
    scorer = LogisticScorer(tmp_path / "missing.joblib")
    with pytest.raises(ModelArtifactUnavailable, match="not found"):
        scorer.score_comment("hello")


def test_api_composition_uses_logistic_artifact(artifact, tmp_path, monkeypatch):
    path, metadata = artifact
    monkeypatch.setenv("MODERATION_MODEL_ARTIFACT_PATH", str(path))
    monkeypatch.setenv("MODERATION_MODEL_METADATA_PATH", str(metadata))
    monkeypatch.setenv("MODERATION_DATABASE_PATH", str(tmp_path / "api.db"))
    password = "Synthetic-test-password-42!"
    with TestClient(create_app()) as client:
        seed_demo_users(client.app.state.database, password, password)
        token = client.post("/auth/login", json={"username": "supervisor", "password": password}).json()["access_token"]
        response = client.post(
            "/comments/import",
            headers={"Authorization": f"Bearer {token}"},
            json={"items": [{"comment_id": "c1", "video_id": "v1", "text": "awful hateful insult"}]},
        )
        assert response.status_code == 201
        row = client.get("/comments", headers={"Authorization": f"Bearer {token}"}).json()["items"][0]
        assert row["score_source"] == "MODEL"
        assert row["model_version"] == "logistic-tfidf-v1"
        assert 0 <= row["risk_score"] <= 1
        assert "text" not in row

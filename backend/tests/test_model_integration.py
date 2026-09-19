"""The real-model boundary with a small synthetic sklearn pipeline."""

import joblib
import pytest
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import make_pipeline

from app.comments.scoring import ModelScorer
from app.main import create_app


def test_model_adapter_scores_synthetic_pipeline(tmp_path):
    model = make_pipeline(TfidfVectorizer(), LogisticRegression(random_state=4))
    model.fit(["safe words", "kind words", "harm words", "attack words"], [0, 0, 1, 1])
    artifact = tmp_path / "tiny.joblib"
    joblib.dump(model, artifact)
    scorer = ModelScorer(artifact, "synthetic-test-v1")
    scores = [scorer.score_comment(text) for text in ("kind words", "attack words")]
    assert all(0 <= score.risk_score <= 1 for score in scores)
    assert all(score.score_source == "MODEL" for score in scores)
    assert scores[1].risk_score > scores[0].risk_score


def test_model_adapter_rejects_missing_artifact(tmp_path):
    with pytest.raises(FileNotFoundError):
        ModelScorer(tmp_path / "missing.joblib", "test-v1")


def test_model_mode_requires_artifact_without_fallback(monkeypatch, tmp_path):
    monkeypatch.setenv("MODERATION_SCORER_MODE", "model")
    monkeypatch.setenv("MODERATION_MODEL_PATH", str(tmp_path / "missing.joblib"))
    with pytest.raises(FileNotFoundError):
        create_app()

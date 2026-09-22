"""Swappable scoring boundary for real and demonstration scoring."""

import hashlib
import json
import math
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

import joblib


@dataclass(frozen=True)
class Score:
    risk_score: float
    uncertainty: float
    model_version: str
    score_source: str

    def __post_init__(self) -> None:
        if not all(math.isfinite(value) and 0 <= value <= 1 for value in (self.risk_score, self.uncertainty)):
            raise ValueError("Invalid score")
        if not self.model_version or self.score_source not in {"SIMULATED", "MODEL"}:
            raise ValueError("Invalid scoring metadata")


class Scorer(Protocol):
    def score_comment(self, text: str) -> Score: ...


class SimulatedScorer:
    """Stable synthetic ordering signal; it has no toxicity meaning."""

    def score_comment(self, text: str) -> Score:
        if not isinstance(text, str) or not text.strip():
            raise ValueError("Comment text must not be empty")
        digest = hashlib.sha256(text.encode("utf-8")).digest()
        return Score(int.from_bytes(digest[:2], "big") / 65535, 1.0, "simulated-v1", "SIMULATED")


class ModelArtifactUnavailable(RuntimeError):
    """The configured model artifact cannot be used for inference."""


class LogisticScorer:
    """Load the fitted TF-IDF + Logistic pipeline once and score new text."""

    MODEL_VERSION = "logistic-tfidf-v1"

    def __init__(self, artifact_path: str | Path, metadata_path: str | Path | None = None):
        self.artifact_path = Path(artifact_path)
        self.metadata_path = Path(metadata_path) if metadata_path else self.artifact_path.with_name("artifact_metadata.json")
        self._model = None
        self._metadata = None

    def _load(self):
        if self._model is not None:
            return self._model
        if not self.artifact_path.is_file():
            raise ModelArtifactUnavailable(f"Logistic model artifact not found: {self.artifact_path}")
        if not self.metadata_path.is_file():
            raise ModelArtifactUnavailable(f"Logistic model metadata not found: {self.metadata_path}")
        try:
            metadata = json.loads(self.metadata_path.read_text(encoding="utf-8"))
            if metadata.get("model_version") != self.MODEL_VERSION:
                raise ValueError("unsupported model version")
            digest = hashlib.sha256(self.artifact_path.read_bytes()).hexdigest()
            if metadata.get("artifact_sha256") != digest:
                raise ValueError("artifact hash mismatch")
            model = joblib.load(self.artifact_path)
            if not hasattr(model, "predict_proba"):
                raise ValueError("artifact does not expose predict_proba")
        except (OSError, ValueError, TypeError, json.JSONDecodeError) as error:
            raise ModelArtifactUnavailable(f"Invalid Logistic model artifact: {self.artifact_path}") from error
        self._model = model
        self._metadata = metadata
        return model

    def score_comment(self, text: str) -> Score:
        if not isinstance(text, str) or not text.strip():
            raise ValueError("Comment text must not be empty")
        probability = float(self._load().predict_proba([text.strip()])[0][1])
        uncertainty = 1.0 - abs(probability - 0.5) * 2.0
        return Score(probability, uncertainty, self.MODEL_VERSION, "MODEL")


def select_scorer(settings) -> Scorer:
    """Use the real model when present; fallback is only for local demos/tests."""
    artifact = Path(settings.model_artifact_path)
    if artifact.is_file():
        return LogisticScorer(artifact, settings.model_metadata_path)
    if settings.allow_simulated_fallback:
        return SimulatedScorer()
    raise ModelArtifactUnavailable(f"Logistic model artifact not found: {artifact}")

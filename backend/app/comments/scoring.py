"""Swappable scoring boundary; the default yields demonstration values only."""

import hashlib
import math
from dataclasses import dataclass
from typing import Protocol
from pathlib import Path



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
        digest = hashlib.sha256(text.encode("utf-8")).digest()
        return Score(int.from_bytes(digest[:2], "big") / 65535, 1.0, "simulated-v1", "SIMULATED")


class ModelScorer:
    """Load an operator-provided trusted sklearn pipeline once at startup."""

    def __init__(self, path: Path, version: str):
        import joblib

        if not path.is_file():
            raise FileNotFoundError(path)
        if not version.strip():
            raise ValueError("Model version is required")
        self.pipeline = joblib.load(path)
        classes = list(self.pipeline.classes_)
        if 1 not in classes:
            raise ValueError("Model must expose positive class 1")
        self.positive_index = classes.index(1)
        self.version = version

    def score_comment(self, text: str) -> Score:
        probability = float(self.pipeline.predict_proba([text])[0][self.positive_index])
        return Score(probability, 1 - abs(2 * probability - 1), self.version, "MODEL")

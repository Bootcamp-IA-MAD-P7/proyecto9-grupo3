"""Swappable scoring boundary; the default yields demonstration values only."""

import hashlib
import math
from dataclasses import dataclass
from typing import Protocol



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

"""Leakage-safe linear SVM baseline for the toxicity signal."""

from __future__ import annotations

from pathlib import Path
from typing import Iterable

import numpy as np
import pandas as pd
from sklearn.calibration import CalibratedClassifierCV
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics import (
    average_precision_score,
    brier_score_loss,
    confusion_matrix,
    f1_score,
    precision_score,
    recall_score,
)
from sklearn.pipeline import Pipeline
from sklearn.svm import LinearSVC


TRAIN_VIDEO_IDS = frozenset(
    {"8HB18hZrhXc", "9pr1oE34bIM", "cT14IbTDW2c", "dDbRyFIkNII", "dG7mZQvaQDk"}
)
VALIDATION_VIDEO_IDS = frozenset({"04kJtp6pVXI", "4rCweDxDqdw", "XRuCW80L9mA"})
TEST_VIDEO_IDS = frozenset({"5vF4si3hoRA", "Dt9-byUhPdg", "TZxEyoplYbI", "bUgKZMSxr3E"})
SPLIT_VIDEO_IDS = {
    "train": TRAIN_VIDEO_IDS,
    "validation": VALIDATION_VIDEO_IDS,
    "test": TEST_VIDEO_IDS,
}
RESULT_COLUMNS = ["CommentId", "y_true", "score", "probability", "prediction", "split"]


def assign_splits(dataset: pd.DataFrame) -> pd.Series:
    """Assign the approved group split without moving or deduplicating rows."""
    groups = {video_id: split for split, ids in SPLIT_VIDEO_IDS.items() for video_id in ids}
    unknown = set(dataset["VideoId"].dropna()) - set(groups) - {"#NAME?"}
    if unknown:
        raise ValueError("Dataset contains VideoId values outside the approved split")
    return dataset["VideoId"].map(groups).fillna(pd.NA).astype("string")


def prepare_dataset(dataset: pd.DataFrame) -> pd.DataFrame:
    """Apply only approved filtering and text normalization."""
    required = {"CommentId", "VideoId", "Text", "IsToxic"}
    missing = required - set(dataset.columns)
    if missing:
        raise ValueError(f"Missing required columns: {sorted(missing)}")
    prepared = dataset.loc[dataset["VideoId"].ne("#NAME?")].copy()
    prepared["Text"] = prepared["Text"].astype("string").str.strip()
    if prepared["Text"].isna().any() or prepared["Text"].eq("").any():
        raise ValueError("Text contains missing or blank rows")
    prepared["split"] = assign_splits(prepared)
    if prepared["split"].isna().any():
        raise ValueError("Some rows do not belong to an approved split")
    return prepared


def build_pipeline(*, calibrate: bool = True) -> Pipeline:
    """Build TF-IDF + linear SVM; calibration is fitted on train only."""
    classifier = LinearSVC(class_weight=None, random_state=42)
    if calibrate:
        classifier = CalibratedClassifierCV(classifier, method="sigmoid", cv=5)
    return Pipeline(
        [
            ("tfidf", TfidfVectorizer()),
            ("classifier", classifier),
        ]
    )


def choose_threshold(y_true: Iterable[bool], probabilities: Iterable[float]) -> float:
    """Choose the validation threshold maximizing F1, with deterministic ties."""
    y_true = np.asarray(list(y_true), dtype=bool)
    probabilities = np.asarray(list(probabilities), dtype=float)
    candidates = np.unique(np.concatenate(([0.0, 0.5, 1.0], probabilities)))
    scores = [f1_score(y_true, probabilities >= threshold, zero_division=0) for threshold in candidates]
    return float(candidates[int(np.argmax(scores))])


def evaluate_split(model: Pipeline, dataset: pd.DataFrame, split: str, threshold: float) -> pd.DataFrame:
    """Predict one split and return the shared, row-level result format."""
    subset = dataset.loc[dataset["split"].eq(split)]
    texts = subset["Text"]
    classifier = model.named_steps["classifier"]
    score = model.decision_function(texts)
    probability = model.predict_proba(texts)[:, 1] if hasattr(classifier, "predict_proba") else np.nan
    return pd.DataFrame(
        {
            "CommentId": subset["CommentId"].to_numpy(),
            "y_true": subset["IsToxic"].astype(bool).to_numpy(),
            "score": np.asarray(score, dtype=float),
            "probability": probability,
            "prediction": np.asarray(probability >= threshold if not np.isnan(probability).all() else score >= 0),
            "split": split,
        }
    )


def summarize_metrics(results: pd.DataFrame) -> dict[str, object]:
    """Compute shared metrics for a result frame containing probabilities."""
    y_true = results["y_true"].astype(bool)
    predicted = results["prediction"].astype(bool)
    metrics: dict[str, object] = {
        "precision": precision_score(y_true, predicted, zero_division=0),
        "recall": recall_score(y_true, predicted, zero_division=0),
        "f1": f1_score(y_true, predicted, zero_division=0),
        "confusion_matrix": confusion_matrix(y_true, predicted).tolist(),
    }
    if results["probability"].notna().all():
        probability = results["probability"].astype(float)
        metrics["pr_auc"] = average_precision_score(y_true, probability)
        metrics["brier_score"] = brier_score_loss(y_true, probability)
    return metrics


def export_results(results: pd.DataFrame, path: str | Path) -> None:
    """Write only the common prediction schema; callers choose an ignored path."""
    results[RESULT_COLUMNS].to_csv(path, index=False)

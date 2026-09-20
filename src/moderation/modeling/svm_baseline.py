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


RESULT_COLUMNS = ["CommentId", "y_true", "score", "probability", "prediction", "split"]
SPLITS = frozenset({"train", "validation", "test"})


def load_common_split(path: str | Path) -> pd.DataFrame:
    """Load and validate the shared row-level partition."""
    split = pd.read_csv(path, dtype={"CommentId": "string", "VideoId": "string", "split": "string"})
    required = {"CommentId", "VideoId", "split"}
    missing = required - set(split.columns)
    if missing:
        raise ValueError(f"Split is missing required columns: {sorted(missing)}")
    if split[list(required)].isna().any().any():
        raise ValueError("Split contains missing identifiers or partitions")
    if not split["split"].isin(SPLITS).all():
        raise ValueError("Split contains an unsupported partition")
    if split["CommentId"].duplicated().any():
        raise ValueError("Split contains duplicate CommentId values")
    return split[["CommentId", "VideoId", "split"]]


def prepare_dataset(dataset: pd.DataFrame, split_path: str | Path) -> pd.DataFrame:
    """Filter excluded rows, normalize text, and apply the shared split."""
    required = {"CommentId", "VideoId", "Text", "IsToxic"}
    missing = required - set(dataset.columns)
    if missing:
        raise ValueError(f"Missing required columns: {sorted(missing)}")
    prepared = dataset.loc[dataset["VideoId"].ne("#NAME?")].copy()
    prepared["Text"] = prepared["Text"].astype("string").str.strip()
    if prepared["Text"].isna().any() or prepared["Text"].eq("").any():
        raise ValueError("Text contains missing or blank rows")
    split = load_common_split(split_path)
    prepared = prepared.merge(split, on="CommentId", how="left", validate="many_to_one", suffixes=("", "_split"))
    if prepared["split"].isna().any():
        raise ValueError("Some rows do not belong to the common split")
    if not prepared["VideoId"].eq(prepared["VideoId_split"]).all():
        raise ValueError("Common split VideoId does not match the dataset")
    return prepared.drop(columns="VideoId_split")


def build_pipeline(*, calibrate: bool = True) -> Pipeline:
    """Build the TF-IDF + linear SVM pipeline."""
    classifier = LinearSVC(class_weight=None, random_state=42)
    if calibrate:
        classifier = CalibratedClassifierCV(classifier, method="sigmoid", cv=5)
    return Pipeline(
        [
            ("tfidf", TfidfVectorizer()),
            ("classifier", classifier),
        ]
    )


def fit_on_train(dataset: pd.DataFrame, *, calibrate: bool = True) -> Pipeline:
    """Fit TF-IDF and the classifier using only the approved train split."""
    train = dataset.loc[dataset["split"].eq("train")]
    if train.empty:
        raise ValueError("The train split contains no rows")
    model = build_pipeline(calibrate=calibrate)
    model.fit(train["Text"], train["IsToxic"].astype(bool))
    return model


def run_baseline(dataset_path: str | Path, split_path: str | Path, output_path: str | Path) -> dict[str, object]:
    """Run train-only fitting, validation thresholding, test evaluation, and export."""
    from src.moderation.data.extract import extract_dataset

    output_path = Path(output_path)
    if output_path.suffix.lower() == ".csv":
        test_output_path = output_path
        validation_output_path = output_path.parent / "svm_tfidf_validation_results.csv"
    else:
        validation_output_path = output_path / "svm_tfidf_validation_results.csv"
        test_output_path = output_path / "svm_tfidf_test_results.csv"
    validation_output_path.parent.mkdir(parents=True, exist_ok=True)

    dataset = prepare_dataset(extract_dataset(dataset_path), split_path)
    model = fit_on_train(dataset)
    validation_for_threshold = evaluate_split(model, dataset, "validation", threshold=0.5)
    threshold = choose_threshold(
        validation_for_threshold["y_true"],
        validation_for_threshold["probability"],
    )
    validation = evaluate_split(model, dataset, "validation", threshold=threshold)
    validation_metrics = summarize_metrics(validation)
    results = evaluate_split(model, dataset, "test", threshold=threshold)
    test_metrics = summarize_metrics(results)
    export_results(validation, validation_output_path)
    export_results(results, test_output_path)
    return {
        "threshold": threshold,
        "validation": validation,
        "validation_metrics": validation_metrics,
        "validation_output_path": validation_output_path,
        "test": results,
        "test_metrics": test_metrics,
        "test_output_path": test_output_path,
    }


def choose_threshold(y_true: Iterable[bool], probabilities: Iterable[float]) -> float:
    """Choose the validation threshold maximizing F1, with deterministic ties."""
    y_true = np.asarray(list(y_true), dtype=bool)
    probabilities = np.asarray(list(probabilities), dtype=float)
    candidates = np.unique(np.concatenate(([0.0, 0.5, 1.0], probabilities)))
    scores = [f1_score(y_true, probabilities >= threshold, zero_division=0) for threshold in candidates]
    return float(candidates[int(np.argmax(scores))])


def evaluate_split(model: Pipeline, dataset: pd.DataFrame, split: str, threshold: float) -> pd.DataFrame:
    """Predict one split using probability as the primary score.

    ``score`` is an optional raw continuous classifier score when the fitted
    classifier exposes ``decision_function``; calibrated SVMs may expose only
    probabilities, in which case it is missing.
    """
    subset = dataset.loc[dataset["split"].eq(split)]
    texts = subset["Text"]
    classifier = model.named_steps["classifier"]
    if not hasattr(classifier, "predict_proba"):
        raise ValueError("The fitted classifier must provide predict_proba")
    probability = model.predict_proba(texts)[:, 1]
    if hasattr(classifier, "decision_function"):
        score = classifier.decision_function(model.named_steps["tfidf"].transform(texts))
    else:
        score = probability
    return pd.DataFrame(
        {
            "CommentId": subset["CommentId"].to_numpy(),
            "y_true": subset["IsToxic"].astype(bool).to_numpy(),
            "score": np.asarray(score, dtype=float),
            "probability": probability,
            "prediction": np.asarray(probability >= threshold),
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
    metrics["pr_auc"] = None
    metrics["brier_score"] = None
    if results["probability"].notna().all() and y_true.nunique() >= 2:
        probability = results["probability"].astype(float)
        metrics["pr_auc"] = average_precision_score(y_true, probability)
        metrics["brier_score"] = brier_score_loss(y_true, probability)
    return metrics


def export_results(results: pd.DataFrame, path: str | Path) -> None:
    """Write only the common prediction schema; callers choose an ignored path."""
    if results["CommentId"].isna().any() or results["CommentId"].duplicated().any():
        raise ValueError("Results must contain unique, non-null CommentId values")
    results[RESULT_COLUMNS].to_csv(path, index=False)

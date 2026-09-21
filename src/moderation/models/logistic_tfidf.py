"""Train and evaluate the TF-IDF + logistic regression baseline."""

import json
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    average_precision_score,
    brier_score_loss,
    confusion_matrix,
    f1_score,
    precision_score,
    recall_score,
)
from sklearn.pipeline import Pipeline

from src.moderation.data.extract import validate_dataset


SPLITS = ("train", "validation", "test")
DEFAULT_THRESHOLD = 0.5
TARGET_RECALL = 0.8
REVIEW_SIZES = (10, 20, 50, 100)


def _read_dataset(dataset_path: str | Path) -> pd.DataFrame:
    # IDs and text are strings even when a CSV column contains only digits.
    # Preserve literal text such as "NA" instead of interpreting it as null.
    dataset = pd.read_csv(
        dataset_path,
        dtype={"CommentId": "string", "VideoId": "string", "Text": "string"},
        keep_default_na=False,
    )
    validate_dataset(dataset)
    return dataset


def load_partitions(dataset_path: str | Path, manifest_path: str | Path) -> dict[str, pd.DataFrame]:
    """Join the agreed split to raw rows and reject incomplete or leaking splits."""
    dataset = _read_dataset(dataset_path)
    manifest = pd.read_csv(manifest_path, dtype="string", keep_default_na=False)
    required = {"CommentId", "VideoId", "split"}
    if not required.issubset(manifest.columns):
        raise ValueError(f"Manifest missing columns: {sorted(required - set(manifest.columns))}")
    for name, frame in (("Dataset", dataset), ("Manifest", manifest)):
        for column in ("CommentId", "VideoId"):
            if (frame[column].isna() | frame[column].str.strip().eq("")).any():
                raise ValueError(f"{name} {column} must be present and nonblank")
    if dataset["CommentId"].isna().any() or dataset["CommentId"].duplicated().any():
        raise ValueError("Dataset CommentId must be present and unique")
    if manifest["CommentId"].isna().any() or manifest["CommentId"].duplicated().any():
        raise ValueError("Manifest CommentId must be present and unique")
    if manifest["VideoId"].isna().any() or manifest["split"].isna().any():
        raise ValueError("Manifest VideoId and split must be present")
    if not manifest["split"].isin(SPLITS).all():
        raise ValueError("Manifest contains an unknown split")
    if manifest["VideoId"].eq("#NAME?").any():
        raise ValueError("Unknown-video rows cannot enter the common split")

    merged = manifest.merge(
        dataset[["CommentId", "VideoId", "Text", "IsToxic"]],
        on="CommentId",
        how="left",
        validate="one_to_one",
        suffixes=("_manifest", "_dataset"),
        indicator=True,
    )
    if not merged["_merge"].eq("both").all():
        raise ValueError("Manifest contains CommentId absent from dataset")
    if not merged["VideoId_manifest"].eq(merged["VideoId_dataset"]).all():
        raise ValueError("VideoId mismatch between manifest and dataset")
    known_ids = set(dataset.loc[dataset["VideoId"].ne("#NAME?"), "CommentId"])
    if set(manifest["CommentId"]) != known_ids:
        raise ValueError("Manifest must include every known-video CommentId exactly once")
    if merged.groupby("VideoId_manifest")["split"].nunique().gt(1).any():
        raise ValueError("VideoId appears in multiple splits")

    partitions = {
        split: merged.loc[merged["split"].eq(split), ["CommentId", "Text", "IsToxic"]].copy()
        for split in SPLITS
    }
    if any(part.empty for part in partitions.values()):
        raise ValueError("Train, validation and test must each contain rows")
    normalized_texts = {
        split: set(part["Text"].str.lower().str.split().str.join(" "))
        for split, part in partitions.items()
    }
    if any(
        normalized_texts[left] & normalized_texts[right]
        for left, right in (("train", "validation"), ("train", "test"), ("validation", "test"))
    ):
        raise ValueError("Identical text appears in multiple splits")
    return partitions


def build_pipeline() -> Pipeline:
    """Keep text representation and classifier together to prevent fit leakage."""
    return Pipeline(
        [
            (
                "tfidf",
                TfidfVectorizer(
                    analyzer="char_wb",
                    ngram_range=(3, 5),
                    min_df=2,
                    sublinear_tf=True,
                ),
            ),
            (
                "logistic",
                LogisticRegression(
                    C=3,
                    class_weight="balanced",
                    max_iter=1000,
                    solver="liblinear",
                    random_state=42,
                ),
            ),
        ]
    )


def select_threshold(
    actual: np.ndarray,
    probability: np.ndarray,
    *,
    target_recall: float = TARGET_RECALL,
) -> float:
    """Choose the highest validation threshold that reaches target recall."""
    if not 0 < target_recall <= 1:
        raise ValueError("target_recall must be in (0, 1]")
    if int(np.sum(actual)) == 0:
        raise ValueError("Threshold selection requires positive validation rows")
    for threshold in sorted(np.unique(probability), reverse=True):
        predicted = probability >= threshold
        if recall_score(actual, predicted) >= target_recall:
            return float(threshold)
    raise RuntimeError("No threshold reaches the requested recall")


def ranking_metrics(
    actual: np.ndarray,
    probability: np.ndarray,
    *,
    review_sizes: tuple[int, ...] = REVIEW_SIZES,
) -> dict[str, dict[str, float | int]]:
    """Measure toxic coverage within reviewable prefixes of the ranked queue."""
    order = np.argsort(-probability, kind="stable")
    positives = int(np.sum(actual))
    metrics = {}
    for size in review_sizes:
        if size > len(actual):
            continue
        found = int(np.sum(actual[order[:size]]))
        metrics[str(size)] = {
            "precision": found / size,
            "recall": found / positives if positives else 0.0,
            "toxic_found": found,
        }
    return metrics


def evaluate(
    model: Pipeline,
    partition: pd.DataFrame,
    *,
    threshold: float = DEFAULT_THRESHOLD,
) -> tuple[pd.DataFrame, dict]:
    """Return aligned probabilities and classification/ranking/calibration metrics."""
    actual = partition["IsToxic"].astype(int).to_numpy()
    probability = model.predict_proba(partition["Text"].str.strip())[:, 1]
    predicted = (probability >= threshold).astype(int)
    predictions = pd.DataFrame(
        {
            "CommentId": partition["CommentId"].to_numpy(),
            "IsToxic": actual,
            "probability": probability,
            "prediction": predicted,
        }
    )
    metrics = {
        "precision": float(precision_score(actual, predicted, zero_division=0)),
        "recall": float(recall_score(actual, predicted, zero_division=0)),
        "f1": float(f1_score(actual, predicted, zero_division=0)),
        "confusion_matrix": confusion_matrix(actual, predicted, labels=[0, 1]).tolist(),
        "pr_auc": float(average_precision_score(actual, probability)),
        "brier_score": float(brier_score_loss(actual, probability)),
        "ranking": ranking_metrics(actual, probability),
    }
    return predictions, metrics


def run_training(
    dataset_path: str | Path,
    manifest_path: str | Path,
    output_dir: str | Path,
    *,
    final_test: bool = False,
    ensemble_config: str | Path | None = None,
) -> dict:
    """Fit on train; export validation and optionally the untouched final test."""
    if final_test:
        if ensemble_config is None:
            raise ValueError("final_test requires a frozen ensemble_config")
        from src.moderation.models.final_test_gate import verify_committed_config
        verify_committed_config(ensemble_config, manifest_path)
    partitions = load_partitions(dataset_path, manifest_path)
    train = partitions["train"]
    if train["IsToxic"].nunique() != 2:
        raise ValueError("Training split must contain both IsToxic classes")
    model = build_pipeline()
    model.fit(train["Text"].str.strip(), train["IsToxic"].astype(int))

    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)
    joblib.dump(model, output / "logistic_tfidf.joblib")
    validation = partitions["validation"]
    validation_actual = validation["IsToxic"].astype(int).to_numpy()
    validation_probability = model.predict_proba(validation["Text"].str.strip())[:, 1]
    threshold = select_threshold(validation_actual, validation_probability)
    validation_predictions, validation_metrics = evaluate(
        model,
        validation,
        threshold=threshold,
    )
    validation_predictions.to_csv(output / "validation_predictions.csv", index=False)
    report = {
        "model": "char-tfidf-logistic-regression-v2",
        "threshold": threshold,
        "threshold_status": "selected_on_validation_for_target_recall",
        "target_recall": TARGET_RECALL,
        "pr_auc_definition": "average_precision",
        "train_rows": len(train),
        "validation_rows": len(partitions["validation"]),
        "test_rows": len(partitions["test"]),
        "excluded_unknown_video_rows": (
            len(_read_dataset(dataset_path)) - sum(map(len, partitions.values()))
        ),
        "validation": validation_metrics,
    }
    if final_test:
        test_predictions, test_metrics = evaluate(
            model,
            partitions["test"],
            threshold=threshold,
        )
        test_predictions.to_csv(output / "test_predictions.csv", index=False)
        report["test"] = test_metrics
    else:
        stale_test = output / "test_predictions.csv"
        if stale_test.exists():
            stale_test.unlink()
    (output / "metrics.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    return report

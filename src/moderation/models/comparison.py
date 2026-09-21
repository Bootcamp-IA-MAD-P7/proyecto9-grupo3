"""Fair validation-only comparison of aligned model probabilities."""

from __future__ import annotations

from collections.abc import Mapping
import json
from pathlib import Path

import pandas as pd

from src.moderation.models.logistic_tfidf import select_threshold
from src.moderation.models.transformer import build_prediction_frame, summarize_predictions


def _normalize(frame: pd.DataFrame) -> pd.DataFrame:
    target = "IsToxic" if "IsToxic" in frame.columns else "y_true"
    required = {"CommentId", target, "probability"}
    if not required.issubset(frame.columns):
        raise ValueError(f"Predictions missing columns: {sorted(required - set(frame.columns))}")
    normalized = frame[["CommentId", target, "probability"]].rename(columns={target: "IsToxic"}).copy()
    normalized["IsToxic"] = normalized["IsToxic"].astype(int)
    if normalized["CommentId"].isna().any() or normalized["CommentId"].duplicated().any():
        raise ValueError("Prediction CommentId values must be unique and non-null")
    return normalized


def compare_validation_predictions(
    frames: Mapping[str, pd.DataFrame],
    *,
    target_recall: float = 0.8,
) -> dict[str, object]:
    """Recompute every decision with the same validation threshold policy."""
    if len(frames) < 2:
        raise ValueError("At least two models are required for comparison")
    normalized = {name: _normalize(frame) for name, frame in frames.items()}
    reference = next(iter(normalized.values()))[["CommentId", "IsToxic"]].reset_index(drop=True)
    reference_ids = reference["CommentId"].tolist()
    reference_labels = reference.set_index("CommentId")["IsToxic"]
    for name, frame in normalized.items():
        if set(frame["CommentId"]) != set(reference_ids):
            raise ValueError("Model predictions must contain the same aligned CommentId values")
        aligned = frame.set_index("CommentId").loc[reference_ids].reset_index()
        labels = aligned.set_index("CommentId")["IsToxic"]
        if not labels.equals(reference_labels):
            raise ValueError("Model predictions contain conflicting ground truth")
        normalized[name] = aligned

    model_metrics: dict[str, dict[str, object]] = {}
    probability_columns: dict[str, pd.Series] = {}
    for name, frame in normalized.items():
        probability = frame["probability"].astype(float).to_numpy()
        threshold = select_threshold(
            frame["IsToxic"].astype(int).to_numpy(),
            probability,
            target_recall=target_recall,
        )
        predictions = build_prediction_frame(frame, probability, threshold=threshold)
        model_metrics[name] = {"threshold": threshold, **summarize_predictions(predictions)}
        probability_columns[name] = frame["probability"].astype(float).reset_index(drop=True)

    correlation = pd.DataFrame(probability_columns).corr().to_dict()
    return {
        "comment_count": len(reference),
        "target_recall": target_recall,
        "models": model_metrics,
        "probability_correlation": correlation,
    }


def compare_prediction_files(
    paths: Mapping[str, str | Path],
    output_path: str | Path,
    *,
    split_path: str | Path,
    target_recall: float = 0.8,
) -> dict[str, object]:
    """Load aligned validation exports and persist an inspectable comparison."""
    manifest = pd.read_csv(
        split_path,
        dtype={"CommentId": "string", "split": "string"},
        keep_default_na=False,
    )
    if not {"CommentId", "split"}.issubset(manifest.columns):
        raise ValueError("Common split must contain CommentId and split")
    validation_ids = set(
        manifest.loc[manifest["split"].eq("validation"), "CommentId"]
    )
    frames = {
        name: pd.read_csv(
            path,
            dtype={"CommentId": "string"},
            keep_default_na=False,
        )
        for name, path in paths.items()
    }
    for name, frame in frames.items():
        if set(frame["CommentId"]) != validation_ids:
            raise ValueError(
                f"{name} predictions must contain exactly the validation split CommentId values"
            )
    report = compare_validation_predictions(frames, target_recall=target_recall)
    output = Path(output_path)
    output.mkdir(parents=True, exist_ok=True)
    (output / "comparison.json").write_text(
        json.dumps(report, indent=2) + "\n", encoding="utf-8"
    )
    rows = [
        {"model": name, **metrics}
        for name, metrics in report["models"].items()
    ]
    pd.DataFrame(rows).to_csv(output / "model_metrics.csv", index=False)
    pd.DataFrame(report["probability_correlation"]).to_csv(
        output / "probability_correlation.csv", index_label="model"
    )
    return report

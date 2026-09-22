"""Weighted soft-voting ensemble for aligned toxicity probabilities."""

from __future__ import annotations

from collections.abc import Mapping
import hashlib
import json
import math
from pathlib import Path

import numpy as np
import pandas as pd

from src.moderation.models.comparison import _normalize
from src.moderation.models.logistic_tfidf import select_threshold
from src.moderation.models.final_test_gate import (
    load_frozen_ensemble_config,
    validate_prediction_metadata,
)
from src.moderation.models.transformer import (
    build_prediction_frame,
    summarize_predictions,
)


MODEL_NAMES = ("logistic", "svm", "transformer")
DEFAULT_WEIGHTS = {"logistic": 0.1, "svm": 0.0, "transformer": 0.9}


def validate_classical_weights(logistic: float, svm: float) -> tuple[float, float]:
    """Validate a two-model Logistic/SVM soft-voting distribution."""
    values = (float(logistic), float(svm))
    if any(not math.isfinite(value) or value < 0 for value in values):
        raise ValueError("Classical ensemble weights must be finite and non-negative")
    if not math.isclose(sum(values), 1.0, rel_tol=0.0, abs_tol=1e-9):
        raise ValueError("Classical ensemble weights must sum to one")
    return values


def validate_weights(weights: Mapping[str, float]) -> dict[str, float]:
    """Require one finite non-negative weight per candidate model summing to one."""
    if set(weights) != set(MODEL_NAMES):
        raise ValueError("Ensemble weights must cover logistic, svm and transformer")
    validated = {name: float(weights[name]) for name in MODEL_NAMES}
    if any(not math.isfinite(value) or value < 0 for value in validated.values()):
        raise ValueError("Ensemble weights must be finite and non-negative")
    if not math.isclose(sum(validated.values()), 1.0, rel_tol=0.0, abs_tol=1e-9):
        raise ValueError("Ensemble weights must sum to one")
    return validated


def _align_components(frames: Mapping[str, pd.DataFrame]) -> dict[str, pd.DataFrame]:
    if set(frames) != set(MODEL_NAMES):
        raise ValueError("Prediction frames must cover logistic, svm and transformer")
    normalized = {name: _normalize(frames[name]) for name in MODEL_NAMES}
    reference = normalized[MODEL_NAMES[0]][["CommentId", "IsToxic"]].reset_index(drop=True)
    reference_ids = reference["CommentId"].tolist()
    reference_labels = reference.set_index("CommentId")["IsToxic"]
    aligned = {}
    for name, frame in normalized.items():
        if set(frame["CommentId"]) != set(reference_ids):
            raise ValueError("Component predictions must contain identical CommentId values")
        ordered = frame.set_index("CommentId").loc[reference_ids].reset_index()
        labels = ordered.set_index("CommentId")["IsToxic"]
        if not labels.equals(reference_labels):
            raise ValueError("Component predictions contain conflicting ground truth")
        aligned[name] = ordered
    return aligned


def build_ensemble_predictions(
    frames: Mapping[str, pd.DataFrame],
    *,
    weights: Mapping[str, float],
    threshold: float,
) -> pd.DataFrame:
    """Combine aligned component probabilities using frozen weights and threshold."""
    validated_weights = validate_weights(weights)
    aligned = _align_components(frames)
    reference = aligned[MODEL_NAMES[0]]
    probabilities = {
        name: aligned[name]["probability"].astype(float).to_numpy()
        for name in MODEL_NAMES
    }
    combined = sum(validated_weights[name] * probabilities[name] for name in MODEL_NAMES)
    predictions = build_prediction_frame(reference, combined, threshold=threshold)
    for name in MODEL_NAMES:
        predictions[f"probability_{name}"] = probabilities[name]
    return predictions


def fit_ensemble(
    frames: Mapping[str, pd.DataFrame],
    *,
    weights: Mapping[str, float] = DEFAULT_WEIGHTS,
    target_recall: float = 0.8,
) -> dict[str, object]:
    """Choose the ensemble threshold from validation probabilities only."""
    combined = build_ensemble_predictions(frames, weights=weights, threshold=0.5)
    threshold = select_threshold(
        combined["IsToxic"].astype(int).to_numpy(),
        combined["probability"].astype(float).to_numpy(),
        target_recall=target_recall,
    )
    predictions = build_ensemble_predictions(frames, weights=weights, threshold=threshold)
    return {
        "weights": validate_weights(weights),
        "target_recall": target_recall,
        "threshold": threshold,
        "predictions": predictions,
        "metrics": summarize_predictions(predictions),
    }


def fit_classical_ensemble(
    logistic_frame: pd.DataFrame,
    svm_frame: pd.DataFrame,
    *,
    logistic_weight: float,
    svm_weight: float,
    target_recall: float = 0.8,
) -> dict[str, object]:
    """Evaluate a Logistic/SVM combination with a validation-only threshold."""
    logistic_weight, svm_weight = validate_classical_weights(
        logistic_weight, svm_weight
    )
    logistic = _normalize(logistic_frame)
    svm = _normalize(svm_frame)
    for name, frame in (("logistic", logistic), ("svm", svm)):
        probability = frame["probability"].astype(float).to_numpy()
        if not np.isfinite(probability).all() or ((probability < 0) | (probability > 1)).any():
            raise ValueError(f"{name} probabilities must be between zero and one")
    if set(logistic["CommentId"]) != set(svm["CommentId"]):
        raise ValueError("Classical predictions must contain identical CommentId values")
    reference_ids = logistic["CommentId"].tolist()
    svm = svm.set_index("CommentId").loc[reference_ids].reset_index()
    if not svm["IsToxic"].equals(logistic["IsToxic"]):
        raise ValueError("Classical predictions contain conflicting ground truth")
    probabilities = (
        logistic_weight * logistic["probability"].astype(float).to_numpy()
        + svm_weight * svm["probability"].astype(float).to_numpy()
    )
    reference = logistic[["CommentId", "IsToxic"]]
    threshold = select_threshold(
        reference["IsToxic"].to_numpy(), probabilities, target_recall=target_recall
    )
    predictions = build_prediction_frame(reference, probabilities, threshold=threshold)
    predictions["probability_logistic"] = logistic["probability"].to_numpy()
    predictions["probability_svm"] = svm["probability"].to_numpy()
    return {
        "weights": {"logistic": logistic_weight, "svm": svm_weight},
        "target_recall": target_recall,
        "threshold": threshold,
        "predictions": predictions,
        "metrics": summarize_predictions(predictions),
    }


def _sha256(path: str | Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _load_component_files(
    paths: Mapping[str, str | Path],
    *,
    split_path: str | Path,
    split: str,
    config_sha256: str | None = None,
) -> dict[str, pd.DataFrame]:
    if set(paths) != set(MODEL_NAMES):
        raise ValueError("Prediction paths must cover logistic, svm and transformer")
    manifest = pd.read_csv(
        split_path,
        dtype={"CommentId": "string", "split": "string"},
        keep_default_na=False,
    )
    if not {"CommentId", "split"}.issubset(manifest.columns):
        raise ValueError("Common split must contain CommentId and split")
    if manifest["CommentId"].duplicated().any():
        raise ValueError("Common split CommentId values must be unique")
    split_ids = manifest.loc[manifest["split"].eq(split), "CommentId"].tolist()
    expected_ids = set(split_ids)
    frames = {}
    for name in MODEL_NAMES:
        frame = pd.read_csv(
            paths[name],
            dtype={"CommentId": "string"},
            keep_default_na=False,
        )
        if "CommentId" not in frame.columns or set(frame["CommentId"]) != expected_ids:
            raise ValueError(
                f"{name} predictions must contain exactly the {split} split CommentId values"
            )
        validate_prediction_metadata(
            paths[name],
            expected_model=name,
            expected_split=split,
            manifest_path=split_path,
            expected_config_sha256=config_sha256,
        )
        frames[name] = frame.set_index("CommentId").loc[split_ids].reset_index()
    return frames


def fit_ensemble_from_files(
    paths: Mapping[str, str | Path],
    *,
    split_path: str | Path,
    output_path: str | Path,
    config_path: str | Path,
    weights: Mapping[str, float] = DEFAULT_WEIGHTS,
    target_recall: float = 0.8,
) -> dict[str, object]:
    """Fit validation-only ensemble decisions and persist a frozen config."""
    config_file = Path(config_path)
    if config_file.exists():
        raise ValueError("Ensemble config already exists; refusing to overwrite it")
    frames = _load_component_files(paths, split_path=split_path, split="validation")
    result = fit_ensemble(frames, weights=weights, target_recall=target_recall)
    source_hashes = {"manifest": _sha256(split_path)}
    source_hashes.update({name: _sha256(paths[name]) for name in MODEL_NAMES})
    config: dict[str, object] = {
        "schema_version": 1,
        "weights": result["weights"],
        "threshold": result["threshold"],
        "target_recall": target_recall,
        "validation_metrics": result["metrics"],
        "source_sha256": source_hashes,
    }
    output = Path(output_path)
    output.mkdir(parents=True, exist_ok=True)
    result["predictions"].to_csv(output / "validation_predictions.csv", index=False)
    (output / "validation_metrics.json").write_text(
        json.dumps(config, indent=2) + "\n", encoding="utf-8"
    )
    config_file.parent.mkdir(parents=True, exist_ok=True)
    config_file.write_text(json.dumps(config, indent=2) + "\n", encoding="utf-8")
    return config


def evaluate_frozen_ensemble_from_files(
    paths: Mapping[str, str | Path],
    *,
    split_path: str | Path,
    config_path: str | Path,
    output_path: str | Path,
) -> dict[str, object]:
    """Apply a frozen validation config to the held-out test exactly once."""
    output = Path(output_path)
    test_predictions_path = output / "test_predictions.csv"
    test_metrics_path = output / "test_metrics.json"
    seal_path = output / ".final-test.seal"
    if test_predictions_path.exists() or test_metrics_path.exists() or seal_path.exists():
        raise ValueError("Final test output already exists; refusing to overwrite it")
    config, config_digest = load_frozen_ensemble_config(config_path, split_path)
    weights = validate_weights(config.get("weights", {}))
    threshold = float(config.get("threshold"))
    if not math.isfinite(threshold) or not 0 <= threshold <= 1:
        raise ValueError("Frozen ensemble threshold must be between zero and one")
    output.mkdir(parents=True, exist_ok=True)
    try:
        with seal_path.open("x", encoding="utf-8") as seal:
            seal.write(config_digest + "\n")
        frames = _load_component_files(
            paths,
            split_path=split_path,
            split="test",
            config_sha256=config_digest,
        )
        predictions = build_ensemble_predictions(
            frames,
            weights=weights,
            threshold=threshold,
        )
        report = {
            "schema_version": 1,
            "weights": weights,
            "threshold": threshold,
            "metrics": summarize_predictions(predictions),
            "source_sha256": {
                "manifest": _sha256(split_path),
                **{name: _sha256(paths[name]) for name in MODEL_NAMES},
                **{
                    f"{name}_metadata": _sha256(
                        Path(paths[name]).with_suffix(Path(paths[name]).suffix + ".metadata.json")
                    )
                    for name in MODEL_NAMES
                },
                "config": config_digest,
            },
        }
        temporary_predictions = output / ".test_predictions.csv.tmp"
        temporary_metrics = output / ".test_metrics.json.tmp"
        predictions.to_csv(temporary_predictions, index=False)
        temporary_metrics.write_text(
            json.dumps(report, indent=2) + "\n", encoding="utf-8"
        )
        temporary_predictions.replace(test_predictions_path)
        temporary_metrics.replace(test_metrics_path)
        return report
    except Exception:
        if not test_predictions_path.exists() and not test_metrics_path.exists():
            seal_path.unlink(missing_ok=True)
        raise

"""Guardrails for opening the final test split."""

from __future__ import annotations

import hashlib
import csv
import json
import math
import subprocess
from pathlib import Path


_COMMITTED_CONFIG_ERROR = (
    "Final-test config must be committed and identical to its version in HEAD"
)


def _git(repository: Path, *arguments: str, text: bool = True) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["git", "-C", str(repository), *arguments],
        check=True,
        capture_output=True,
        text=text,
    )


def load_frozen_ensemble_config(
    config_path: str | Path, manifest_path: str | Path
) -> tuple[dict[str, object], str]:
    """Load validated ensemble bytes from HEAD and return config plus digest."""

    config = Path(config_path).resolve()
    if not config.is_file():
        raise ValueError(_COMMITTED_CONFIG_ERROR)

    try:
        repository = Path(
            _git(config.parent, "rev-parse", "--show-toplevel").stdout.strip()
        ).resolve()
        manifest_repository = Path(
            _git(Path(manifest_path).resolve().parent, "rev-parse", "--show-toplevel").stdout.strip()
        ).resolve()
        if repository != manifest_repository:
            raise ValueError(_COMMITTED_CONFIG_ERROR)
        relative = config.relative_to(repository).as_posix()
        if relative != "configs/ensemble.json":
            raise ValueError(_COMMITTED_CONFIG_ERROR)
        _git(repository, "ls-files", "--error-unmatch", "--", relative)
        _git(repository, "diff", "--quiet", "HEAD", "--", relative)
        committed = _git(repository, "show", f"HEAD:{relative}", text=False).stdout
    except (OSError, subprocess.CalledProcessError, ValueError) as error:
        raise ValueError(_COMMITTED_CONFIG_ERROR) from error

    try:
        parsed = json.loads(committed.decode("utf-8"))
        weights = parsed["weights"]
        threshold = float(parsed["threshold"])
        valid_weights = (
            set(weights) == {"logistic", "svm", "transformer"}
            and all(math.isfinite(float(value)) and float(value) >= 0 for value in weights.values())
            and math.isclose(sum(map(float, weights.values())), 1.0, abs_tol=1e-9)
        )
        valid = (
            parsed.get("schema_version") == 1
            and valid_weights
            and math.isfinite(threshold)
            and 0 <= threshold <= 1
            and parsed.get("source_sha256", {}).get("manifest") == _sha256(manifest_path)
        )
    except (KeyError, TypeError, ValueError, UnicodeDecodeError, json.JSONDecodeError) as error:
        raise ValueError(_COMMITTED_CONFIG_ERROR) from error
    if not valid:
        raise ValueError(_COMMITTED_CONFIG_ERROR)
    return parsed, hashlib.sha256(committed).hexdigest()


def verify_committed_config(config_path: str | Path, manifest_path: str | Path) -> str:
    """Return the digest of a valid frozen ensemble config stored in HEAD."""

    return load_frozen_ensemble_config(config_path, manifest_path)[1]


def _sha256(path: str | Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def _metadata_path(prediction_path: str | Path) -> Path:
    prediction = Path(prediction_path)
    return prediction.with_suffix(prediction.suffix + ".metadata.json")


def write_prediction_metadata(
    prediction_path: str | Path,
    *,
    model_name: str,
    split: str,
    manifest_path: str | Path,
    config_sha256: str | None = None,
) -> Path:
    """Write a provenance sidecar for a Text-only component prediction file."""

    metadata = {
        "schema_version": 1,
        "model_name": model_name,
        "split": split,
        "feature_columns": ["Text"],
        "target": "IsToxic",
        "manifest_sha256": _sha256(manifest_path),
        "predictions_sha256": _sha256(prediction_path),
    }
    if split == "test":
        if config_sha256 is None:
            raise ValueError("Test prediction metadata requires the frozen config digest")
        metadata["config_sha256"] = config_sha256
    path = _metadata_path(prediction_path)
    path.write_text(json.dumps(metadata, indent=2) + "\n", encoding="utf-8")
    return path


def validate_prediction_metadata(
    prediction_path: str | Path,
    *,
    expected_model: str,
    expected_split: str,
    manifest_path: str | Path,
    expected_config_sha256: str | None = None,
) -> dict[str, object]:
    """Validate the component identity and immutable inputs recorded by its sidecar."""

    try:
        metadata = json.loads(_metadata_path(prediction_path).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise ValueError("Missing or invalid prediction metadata") from error
    expected = {
        "schema_version": 1,
        "model_name": expected_model,
        "split": expected_split,
        "feature_columns": ["Text"],
        "target": "IsToxic",
        "manifest_sha256": _sha256(manifest_path),
        "predictions_sha256": _sha256(prediction_path),
    }
    if expected_split == "test":
        expected["config_sha256"] = expected_config_sha256
    if any(metadata.get(key) != value for key, value in expected.items()):
        raise ValueError("Prediction metadata does not match the requested artifact")
    with Path(prediction_path).open("r", encoding="utf-8-sig", newline="") as source:
        columns = set(next(csv.reader(source), []))
    required = {"CommentId", "probability", "y_true" if expected_model == "svm" else "IsToxic"}
    allowed = required | ({"score", "prediction", "split"} if expected_model == "svm" else {"prediction"})
    if not required.issubset(columns) or not columns.issubset(allowed):
        raise ValueError("Prediction metadata does not match the model column contract")
    return metadata

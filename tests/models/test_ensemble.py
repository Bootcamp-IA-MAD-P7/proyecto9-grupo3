import json
import subprocess

import pandas as pd
import pytest

from src.moderation.models.ensemble import (
    build_ensemble_predictions,
    evaluate_frozen_ensemble_from_files,
    fit_ensemble,
    fit_ensemble_from_files,
    validate_weights,
)
from src.moderation.models.final_test_gate import write_prediction_metadata


def component_frame(probabilities, *, reverse=False):
    frame = pd.DataFrame(
        {
            "CommentId": ["a", "b", "c", "d"],
            "IsToxic": [0, 1, 1, 0],
            "probability": probabilities,
        }
    )
    if reverse:
        return frame.iloc[::-1].reset_index(drop=True)
    return frame


def test_soft_voting_aligns_ids_and_applies_frozen_weights_and_threshold():
    frames = {
        "logistic": component_frame([0.2, 0.8, 0.7, 0.1]),
        "svm": component_frame([0.1, 0.9, 0.6, 0.2], reverse=True),
        "transformer": component_frame([0.4, 0.6, 0.9, 0.3]),
    }

    predictions = build_ensemble_predictions(
        frames,
        weights={"logistic": 0.1, "svm": 0.0, "transformer": 0.9},
        threshold=0.5,
    )

    assert predictions["CommentId"].tolist() == ["a", "b", "c", "d"]
    assert predictions["probability"].tolist() == pytest.approx([0.38, 0.62, 0.88, 0.28])
    assert predictions["prediction"].tolist() == [0, 1, 1, 0]
    assert predictions["probability_svm"].tolist() == pytest.approx([0.1, 0.9, 0.6, 0.2])


@pytest.mark.parametrize(
    "weights",
    [
        {"logistic": 0.1, "transformer": 0.9},
        {"logistic": 0.1, "svm": -0.1, "transformer": 1.0},
        {"logistic": 0.2, "svm": 0.2, "transformer": 0.2},
        {"logistic": float("nan"), "svm": 0.0, "transformer": 1.0},
    ],
)
def test_weights_must_cover_three_models_and_form_a_probability_distribution(weights):
    with pytest.raises(ValueError, match="weights"):
        validate_weights(weights)


def test_fit_ensemble_selects_threshold_only_from_combined_validation_probabilities():
    frames = {
        "logistic": component_frame([0.1, 0.8, 0.7, 0.2]),
        "svm": component_frame([0.2, 0.7, 0.6, 0.1]),
        "transformer": component_frame([0.3, 1.0, 0.9, 0.4]),
    }

    result = fit_ensemble(
        frames,
        weights={"logistic": 0.1, "svm": 0.0, "transformer": 0.9},
        target_recall=0.8,
    )

    assert result["threshold"] == pytest.approx(0.88)
    assert result["metrics"]["recall"] == 1.0
    assert result["metrics"]["precision"] == 1.0
    assert result["predictions"]["probability"].tolist() == pytest.approx(
        [0.28, 0.98, 0.88, 0.38]
    )


def write_component_files(tmp_path, prefix, comment_ids, labels, probabilities):
    paths = {}
    for name, values in probabilities.items():
        target = "y_true" if name == "svm" else "IsToxic"
        frame = pd.DataFrame(
            {"CommentId": comment_ids, target: labels, "probability": values}
        )
        path = tmp_path / f"{prefix}-{name}.csv"
        frame.to_csv(path, index=False)
        paths[name] = path
    return paths


def common_manifest(tmp_path):
    path = tmp_path / "common_split.csv"
    pd.DataFrame(
        {
            "CommentId": ["a", "b", "c", "d", "test-a", "test-b"],
            "VideoId": ["validation-video"] * 4 + ["test-video"] * 2,
            "split": ["validation"] * 4 + ["test"] * 2,
        }
    ).to_csv(path, index=False)
    return path


def commit_frozen_config(tmp_path, config_path):
    subprocess.run(["git", "-C", str(tmp_path), "init"], check=True, capture_output=True)
    subprocess.run(
        ["git", "-C", str(tmp_path), "config", "user.email", "tests@example.com"],
        check=True,
    )
    subprocess.run(
        ["git", "-C", str(tmp_path), "config", "user.name", "Tests"], check=True
    )
    subprocess.run(["git", "-C", str(tmp_path), "add", str(config_path)], check=True)
    subprocess.run(
        ["git", "-C", str(tmp_path), "commit", "-m", "freeze ensemble"],
        check=True,
        capture_output=True,
    )


def add_metadata(paths, split_path, split, config_sha256=None):
    for name, path in paths.items():
        write_prediction_metadata(
            path,
            model_name=name,
            split=split,
            manifest_path=split_path,
            config_sha256=config_sha256,
        )


def test_fit_from_files_freezes_config_and_exports_validation_artifacts(tmp_path):
    split_path = common_manifest(tmp_path)
    paths = write_component_files(
        tmp_path,
        "validation",
        ["a", "b", "c", "d"],
        [0, 1, 1, 0],
        {
            "logistic": [0.1, 0.8, 0.7, 0.2],
            "svm": [0.2, 0.7, 0.6, 0.1],
            "transformer": [0.3, 1.0, 0.9, 0.4],
        },
    )
    add_metadata(paths, split_path, "validation")
    output_path = tmp_path / "ensemble"
    config_path = tmp_path / "config" / "ensemble.json"

    report = fit_ensemble_from_files(
        paths,
        split_path=split_path,
        output_path=output_path,
        config_path=config_path,
    )

    config = json.loads(config_path.read_text(encoding="utf-8"))
    assert config["weights"] == {"logistic": 0.1, "svm": 0.0, "transformer": 0.9}
    assert config["threshold"] == pytest.approx(0.88)
    assert config["validation_metrics"]["pr_auc"] == pytest.approx(1.0)
    assert set(config["source_sha256"]) == {"manifest", "logistic", "svm", "transformer"}
    assert report == config
    exported = pd.read_csv(output_path / "validation_predictions.csv")
    assert exported["CommentId"].tolist() == ["a", "b", "c", "d"]
    assert (output_path / "validation_metrics.json").exists()

    with pytest.raises(ValueError, match="config already exists"):
        fit_ensemble_from_files(
            paths,
            split_path=split_path,
            output_path=output_path,
            config_path=config_path,
        )


def test_final_evaluation_uses_frozen_threshold_without_refitting_on_test(tmp_path):
    split_path = common_manifest(tmp_path)
    validation_paths = write_component_files(
        tmp_path,
        "validation",
        ["a", "b", "c", "d"],
        [0, 1, 1, 0],
        {
            "logistic": [0.1, 0.8, 0.7, 0.2],
            "svm": [0.2, 0.7, 0.6, 0.1],
            "transformer": [0.3, 1.0, 0.9, 0.4],
        },
    )
    add_metadata(validation_paths, split_path, "validation")
    config_path = tmp_path / "configs" / "ensemble.json"
    fit_ensemble_from_files(
        validation_paths,
        split_path=split_path,
        output_path=tmp_path / "validation-output",
        config_path=config_path,
    )
    commit_frozen_config(tmp_path, config_path)
    from src.moderation.models.final_test_gate import verify_committed_config
    config_sha256 = verify_committed_config(config_path, split_path)
    test_paths = write_component_files(
        tmp_path,
        "test",
        ["test-a", "test-b"],
        [1, 0],
        {
            "logistic": [0.8, 0.5],
            "svm": [0.9, 0.4],
            "transformer": [0.8, 0.6],
        },
    )
    add_metadata(test_paths, split_path, "test", config_sha256)

    report = evaluate_frozen_ensemble_from_files(
        test_paths,
        split_path=split_path,
        config_path=config_path,
        output_path=tmp_path / "test-output",
    )

    predictions = pd.read_csv(tmp_path / "test-output" / "test_predictions.csv")
    assert report["threshold"] == pytest.approx(0.88)
    assert predictions["probability"].tolist() == pytest.approx([0.8, 0.59])
    assert predictions["prediction"].tolist() == [0, 0]
    assert report["metrics"]["recall"] == 0.0


def test_final_evaluation_rejects_validation_ids_and_existing_test_output(tmp_path):
    split_path = common_manifest(tmp_path)
    validation_paths = write_component_files(
        tmp_path,
        "validation",
        ["a", "b", "c", "d"],
        [0, 1, 1, 0],
        {
            "logistic": [0.1, 0.8, 0.7, 0.2],
            "svm": [0.2, 0.7, 0.6, 0.1],
            "transformer": [0.3, 1.0, 0.9, 0.4],
        },
    )
    add_metadata(validation_paths, split_path, "validation")
    config_path = tmp_path / "configs" / "ensemble.json"
    fit_ensemble_from_files(
        validation_paths,
        split_path=split_path,
        output_path=tmp_path / "validation-output",
        config_path=config_path,
    )
    commit_frozen_config(tmp_path, config_path)

    with pytest.raises(ValueError, match="test split"):
        evaluate_frozen_ensemble_from_files(
            validation_paths,
            split_path=split_path,
            config_path=config_path,
            output_path=tmp_path / "test-output",
        )

    test_output = tmp_path / "already-opened"
    test_output.mkdir()
    (test_output / "test_predictions.csv").write_text("sealed", encoding="utf-8")
    with pytest.raises(ValueError, match="already exists"):
        evaluate_frozen_ensemble_from_files(
            validation_paths,
            split_path=split_path,
            config_path=config_path,
            output_path=test_output,
        )

    metrics_output = tmp_path / "metrics-already-opened"
    metrics_output.mkdir()
    (metrics_output / "test_metrics.json").write_text("sealed", encoding="utf-8")
    with pytest.raises(ValueError, match="already exists"):
        evaluate_frozen_ensemble_from_files(
            validation_paths,
            split_path=split_path,
            config_path=config_path,
            output_path=metrics_output,
        )

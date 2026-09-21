import pandas as pd
import pytest

from src.moderation.models.comparison import (
    compare_prediction_files,
    compare_validation_predictions,
)


def prediction_frame(probabilities):
    return pd.DataFrame(
        {
            "CommentId": ["a", "b", "c", "d"],
            "IsToxic": [0, 1, 1, 0],
            "probability": probabilities,
        }
    )


def test_comparison_uses_one_recall_rule_and_reports_probability_correlation():
    frames = {
        "logistic": prediction_frame([0.1, 0.8, 0.7, 0.2]),
        "svm": prediction_frame([0.2, 0.7, 0.6, 0.1]),
        "transformer": prediction_frame([0.3, 1.0, 0.9, 0.4]),
    }

    report = compare_validation_predictions(frames, target_recall=0.8)

    assert report["models"]["logistic"]["recall"] == 1.0
    assert report["models"]["svm"]["recall"] == 1.0
    assert report["models"]["transformer"]["recall"] == 1.0
    assert report["models"]["logistic"]["threshold"] == pytest.approx(0.7)
    assert report["probability_correlation"]["logistic"]["transformer"] == pytest.approx(1.0)
    assert report["comment_count"] == 4


def test_comparison_aligns_same_comments_when_file_order_differs():
    logistic = prediction_frame([0.1, 0.8, 0.7, 0.2])
    misaligned = prediction_frame([0.2, 0.7, 0.6, 0.1]).iloc[::-1].reset_index(drop=True)

    report = compare_validation_predictions({"logistic": logistic, "svm": misaligned})

    assert report["comment_count"] == 4
    assert report["models"]["svm"]["recall"] == 1.0


def test_comparison_rejects_conflicting_ground_truth_for_same_comment():
    logistic = prediction_frame([0.1, 0.8, 0.7, 0.2])
    conflicting = prediction_frame([0.2, 0.7, 0.6, 0.1])
    conflicting.loc[conflicting["CommentId"].eq("b"), "IsToxic"] = 0

    with pytest.raises(ValueError, match="ground truth"):
        compare_validation_predictions({"logistic": logistic, "svm": conflicting})


def test_comparison_accepts_svm_y_true_schema_without_trusting_its_prediction():
    logistic = prediction_frame([0.1, 0.8, 0.7, 0.2])
    svm = pd.DataFrame(
        {
            "CommentId": ["a", "b", "c", "d"],
            "y_true": [False, True, True, False],
            "probability": [0.2, 0.7, 0.6, 0.1],
            "prediction": [True, False, False, True],
            "split": ["validation"] * 4,
        }
    )

    report = compare_validation_predictions({"logistic": logistic, "svm": svm})

    assert report["models"]["svm"]["precision"] == 1.0
    assert report["models"]["svm"]["recall"] == 1.0


def test_file_comparison_exports_inspectable_json_and_csv(tmp_path):
    paths = {}
    for name, probabilities in {
        "logistic": [0.1, 0.8, 0.7, 0.2],
        "svm": [0.2, 0.7, 0.6, 0.1],
        "transformer": [0.3, 1.0, 0.9, 0.4],
    }.items():
        path = tmp_path / f"{name}.csv"
        prediction_frame(probabilities).to_csv(path, index=False)
        paths[name] = path
    split_path = tmp_path / "common_split.csv"
    pd.DataFrame(
        {
            "CommentId": ["a", "b", "c", "d", "test-a"],
            "VideoId": ["validation-video"] * 4 + ["test-video"],
            "split": ["validation"] * 4 + ["test"],
        }
    ).to_csv(split_path, index=False)

    report = compare_prediction_files(paths, tmp_path / "comparison", split_path=split_path)

    assert report["comment_count"] == 4
    table = pd.read_csv(tmp_path / "comparison" / "model_metrics.csv")
    assert table["model"].tolist() == ["logistic", "svm", "transformer"]
    assert set(table.columns) >= {"model", "threshold", "precision", "recall", "f1", "pr_auc", "brier_score"}
    assert (tmp_path / "comparison" / "comparison.json").exists()
    assert (tmp_path / "comparison" / "probability_correlation.csv").exists()


def test_file_comparison_rejects_test_prediction_ids(tmp_path):
    split_path = tmp_path / "common_split.csv"
    pd.DataFrame(
        {
            "CommentId": ["validation-a", "test-a"],
            "VideoId": ["validation-video", "test-video"],
            "split": ["validation", "test"],
        }
    ).to_csv(split_path, index=False)
    paths = {}
    for name in ("logistic", "svm"):
        path = tmp_path / f"{name}.csv"
        pd.DataFrame(
            {"CommentId": ["test-a"], "IsToxic": [1], "probability": [0.9]}
        ).to_csv(path, index=False)
        paths[name] = path

    with pytest.raises(ValueError, match="validation split"):
        compare_prediction_files(paths, tmp_path / "comparison", split_path=split_path)

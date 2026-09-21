import pandas as pd
import pytest

from src.moderation.modeling.svm_baseline import (
    RESULT_COLUMNS,
    choose_threshold,
    evaluate_split,
    export_results,
    fit_on_train,
    load_common_split,
    prepare_dataset,
    run_baseline,
    summarize_metrics,
)


def synthetic_dataset() -> tuple[pd.DataFrame, pd.DataFrame]:
    rows = []
    split_rows = []
    for index in range(10):
        comment_id = f"train-{index}"
        rows.append({"CommentId": comment_id, "VideoId": "train-video", "Text": " train token ", "IsToxic": index % 2})
        split_rows.append({"CommentId": comment_id, "VideoId": "train-video", "split": "train"})
    rows.extend(
        [
            {"CommentId": "validation-row", "VideoId": "validation-video", "Text": " validation token ", "IsToxic": 0},
            {"CommentId": "test-row", "VideoId": "test-video", "Text": " test token ", "IsToxic": 1},
            {"CommentId": "train-0", "VideoId": "train-video", "Text": " duplicate row ", "IsToxic": 1},
            {"CommentId": "excluded", "VideoId": "#NAME?", "Text": "excluded text", "IsToxic": 0},
        ]
    )
    split_rows.extend(
        [
            {"CommentId": "validation-row", "VideoId": "validation-video", "split": "validation"},
            {"CommentId": "test-row", "VideoId": "test-video", "split": "test"},
        ]
    )
    return pd.DataFrame(rows), pd.DataFrame(split_rows)


def test_common_split_is_applied_and_duplicates_are_preserved(tmp_path):
    raw, split = synthetic_dataset()
    split_path = tmp_path / "common_split.csv"
    split.to_csv(split_path, index=False)
    dataset = prepare_dataset(raw, split_path)
    assert set(dataset["split"]) == {"train", "validation", "test"}
    assert len(dataset) == len(raw) - 1
    assert (dataset["CommentId"] == "train-0").sum() == 2
    assert load_common_split(split_path).shape == (12, 3)


def test_prepare_excludes_name_marker_and_strips_text(tmp_path):
    raw, split = synthetic_dataset()
    split_path = tmp_path / "common_split.csv"
    split.to_csv(split_path, index=False)
    dataset = prepare_dataset(raw, split_path)
    assert "#NAME?" not in set(dataset["VideoId"])
    assert dataset["Text"].iloc[0] == "train token"


def test_unknown_video_id_is_rejected(tmp_path):
    raw, split = synthetic_dataset()
    raw.loc[0, "CommentId"] = "unknown"
    split.loc[split["CommentId"] == "train-0", "CommentId"] = "different"
    split_path = tmp_path / "common_split.csv"
    split.to_csv(split_path, index=False)
    with pytest.raises(ValueError, match="common split"):
        prepare_dataset(raw, split_path)


def test_fit_on_train_excludes_validation_and_test_text_from_tfidf(tmp_path):
    raw, split = synthetic_dataset()
    raw.loc[raw["CommentId"] == "validation-row", "Text"] = "validation leakage token"
    raw.loc[raw["CommentId"] == "test-row", "Text"] = "test leakage token"
    split_path = tmp_path / "common_split.csv"
    split.to_csv(split_path, index=False)
    dataset = prepare_dataset(raw, split_path)

    model = fit_on_train(dataset, calibrate=False)

    vocabulary = model.named_steps["tfidf"].vocabulary_
    assert "train" in vocabulary
    assert "validation" not in vocabulary
    assert "test" not in vocabulary
    assert "leakage" not in vocabulary


def test_fit_on_train_calibrates_only_the_train_rows(tmp_path):
    raw, split = synthetic_dataset()
    split_path = tmp_path / "common_split.csv"
    split.to_csv(split_path, index=False)
    dataset = prepare_dataset(raw, split_path)

    model = fit_on_train(dataset, calibrate=True)

    calibrated = model.named_steps["classifier"]
    assert len(calibrated.calibrated_classifiers_) == 5
    assert all(estimator.estimator.classes_.tolist() == [False, True] for estimator in calibrated.calibrated_classifiers_)


def test_evaluate_split_returns_common_output_for_calibrated_pipeline(tmp_path):
    raw, split = synthetic_dataset()
    split_path = tmp_path / "common_split.csv"
    split.to_csv(split_path, index=False)
    dataset = prepare_dataset(raw, split_path)
    model = fit_on_train(dataset)

    results = evaluate_split(model, dataset, "validation", threshold=0.5)

    assert list(results.columns) == ["CommentId", "y_true", "score", "probability", "prediction", "split"]
    assert len(results) == 1
    assert results["probability"].between(0, 1).all()
    assert results["score"].notna().all()
    assert results["score"].equals(results["probability"])


def test_choose_threshold_maximizes_f1_deterministically():
    threshold = choose_threshold(
        [False, True, True, False],
        [0.1, 0.4, 0.8, 0.9],
    )

    assert threshold == 0.4


def test_summarize_metrics_returns_classification_and_probability_metrics():
    results = pd.DataFrame(
        {
            "y_true": [False, True, True, False],
            "prediction": [False, True, False, True],
            "probability": [0.1, 0.8, 0.4, 0.7],
        }
    )

    metrics = summarize_metrics(results)

    assert metrics["precision"] == pytest.approx(0.5)
    assert metrics["recall"] == pytest.approx(0.5)
    assert metrics["f1"] == pytest.approx(0.5)
    assert metrics["confusion_matrix"] == [[1, 1], [1, 1]]
    assert metrics["pr_auc"] == pytest.approx(5 / 6)
    assert metrics["brier_score"] == pytest.approx(0.225)


def test_summarize_metrics_returns_none_for_single_class_probability_metrics():
    results = pd.DataFrame(
        {
            "y_true": [False, False],
            "prediction": [False, True],
            "probability": [0.1, 0.7],
        }
    )

    metrics = summarize_metrics(results)

    assert metrics["pr_auc"] is None
    assert metrics["brier_score"] is None


def test_export_results_writes_only_result_columns(tmp_path):
    results = pd.DataFrame(
        {
            "CommentId": ["comment-1"],
            "y_true": [True],
            "score": [0.8],
            "probability": [0.7],
            "prediction": [True],
            "split": ["test"],
            "internal": ["must not export"],
        }
    )
    output_path = tmp_path / "results.csv"

    export_results(results, output_path)

    exported = pd.read_csv(output_path)
    assert exported.columns.tolist() == RESULT_COLUMNS
    assert exported["CommentId"].tolist() == ["comment-1"]


def test_export_results_rejects_null_or_duplicate_comment_ids(tmp_path):
    results = pd.DataFrame(
        {
            "CommentId": ["duplicate", "duplicate"],
            "y_true": [True, False],
            "score": [0.8, 0.2],
            "probability": [0.7, 0.1],
            "prediction": [True, False],
            "split": ["validation", "validation"],
        }
    )

    with pytest.raises(ValueError, match="unique, non-null CommentId"):
        export_results(results, tmp_path / "results.csv")


@pytest.mark.parametrize("final_test", [False, True])
def test_run_baseline_gates_test_evaluation_and_export(tmp_path, final_test):
    rows = []
    split_rows = []
    for index in range(10):
        comment_id = f"train-{index}"
        rows.append(
            {
                "CommentId": comment_id,
                "VideoId": "train-video",
                "Text": f"train token {index}",
                "IsToxic": index % 2,
            }
        )
        split_rows.append(
            {
                "CommentId": comment_id,
                "VideoId": "train-video",
                "split": "train",
            }
        )
    rows.extend(
        [
            {
                "CommentId": "validation-0",
                "VideoId": "validation-video",
                "Text": "validation unique token",
                "IsToxic": 0,
            },
            {
                "CommentId": "validation-1",
                "VideoId": "validation-video",
                "Text": "validation unique token toxic",
                "IsToxic": 1,
            },
            {
                "CommentId": "test-0",
                "VideoId": "test-video",
                "Text": "test unique token",
                "IsToxic": 0,
            },
            {
                "CommentId": "test-1",
                "VideoId": "test-video",
                "Text": "test unique token toxic",
                "IsToxic": 1,
            },
        ]
    )
    split_rows.extend(
        [
            {"CommentId": "validation-0", "VideoId": "validation-video", "split": "validation"},
            {"CommentId": "validation-1", "VideoId": "validation-video", "split": "validation"},
            {"CommentId": "test-0", "VideoId": "test-video", "split": "test"},
            {"CommentId": "test-1", "VideoId": "test-video", "split": "test"},
        ]
    )
    dataset_path = tmp_path / "dataset.csv"
    split_path = tmp_path / "common_split.csv"
    output_path = tmp_path / "results"
    pd.DataFrame(rows).to_csv(dataset_path, index=False)
    pd.DataFrame(split_rows).to_csv(split_path, index=False)

    result = run_baseline(dataset_path, split_path, output_path, final_test=final_test)

    expected_keys = {
        "threshold",
        "validation",
        "validation_metrics",
        "validation_output_path",
    }
    if final_test:
        expected_keys.update({"test", "test_metrics", "test_output_path"})
    assert set(result) == expected_keys
    assert set(result["validation"]["split"]) == {"validation"}
    assert isinstance(result["threshold"], float)
    assert (
        result["validation"]["prediction"]
        == (result["validation"]["probability"] >= result["threshold"])
    ).all()
    assert result["validation_metrics"] == summarize_metrics(result["validation"])
    assert "f1" in result["validation_metrics"]
    validation_output = tmp_path / "results" / "svm_tfidf_validation_results.csv"
    test_output = tmp_path / "results" / "svm_tfidf_test_results.csv"
    assert result["validation_output_path"] == validation_output
    assert pd.read_csv(validation_output).columns.tolist() == RESULT_COLUMNS
    assert pd.read_csv(validation_output)["split"].tolist() == ["validation", "validation"]
    assert pd.read_csv(validation_output)["CommentId"].is_unique
    if final_test:
        assert set(result["test"]["split"]) == {"test"}
        assert "pr_auc" in result["test_metrics"]
        assert result["test_output_path"] == test_output
        assert pd.read_csv(test_output).columns.tolist() == RESULT_COLUMNS
        assert pd.read_csv(test_output)["split"].tolist() == ["test", "test"]
        assert pd.read_csv(test_output)["CommentId"].is_unique
    else:
        assert not test_output.exists()


def test_default_svm_run_rejects_stale_test_predictions(tmp_path):
    output_path = tmp_path / "results"
    output_path.mkdir()
    (output_path / "svm_tfidf_test_results.csv").write_text("sensitive", encoding="utf-8")

    with pytest.raises(ValueError, match="stale svm_tfidf_test_results"):
        run_baseline(
            tmp_path / "missing-dataset.csv",
            tmp_path / "missing-split.csv",
            output_path,
        )

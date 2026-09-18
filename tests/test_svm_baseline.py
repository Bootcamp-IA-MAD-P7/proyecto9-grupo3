import pandas as pd
import pytest

from src.moderation.modeling.svm_baseline import (
    evaluate_split,
    fit_on_train,
    load_common_split,
    prepare_dataset,
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

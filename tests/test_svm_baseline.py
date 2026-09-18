import pandas as pd
import pytest

from src.moderation.modeling.svm_baseline import (
    TEST_VIDEO_IDS,
    TRAIN_VIDEO_IDS,
    VALIDATION_VIDEO_IDS,
    assign_splits,
    fit_on_train,
    prepare_dataset,
)


def synthetic_dataset() -> pd.DataFrame:
    rows = []
    for index, video_id in enumerate(
        [next(iter(TRAIN_VIDEO_IDS)), next(iter(VALIDATION_VIDEO_IDS)), next(iter(TEST_VIDEO_IDS))]
    ):
        rows.append({"CommentId": f"synthetic-{index}", "VideoId": video_id, "Text": " synthetic text ", "IsToxic": index % 2})
    rows.append({"CommentId": "synthetic-duplicate", "VideoId": rows[0]["VideoId"], "Text": " synthetic text ", "IsToxic": 1})
    rows.append({"CommentId": "excluded", "VideoId": "#NAME?", "Text": "excluded text", "IsToxic": 0})
    return pd.DataFrame(rows)


def test_assign_splits_keeps_video_groups_together():
    dataset = prepare_dataset(synthetic_dataset())
    assert set(dataset["split"]) == {"train", "validation", "test"}
    assert dataset.groupby("VideoId")["split"].nunique().max() == 1
    assert len(dataset) == 4


def test_prepare_excludes_name_marker_and_preserves_duplicates():
    dataset = prepare_dataset(synthetic_dataset())
    assert "#NAME?" not in set(dataset["VideoId"])
    assert len(dataset) == 4
    assert dataset["Text"].tolist().count("synthetic text") == 4


def test_unknown_video_id_is_rejected():
    dataset = synthetic_dataset().iloc[:1].copy()
    dataset.loc[0, "VideoId"] = "unknown-video"
    with pytest.raises(ValueError, match="outside the approved split"):
        prepare_dataset(dataset)


def test_fit_on_train_excludes_validation_and_test_text_from_tfidf():
    rows = []
    for index, video_id in enumerate(TRAIN_VIDEO_IDS):
        rows.append(
            {
                "CommentId": f"train-{index}",
                "VideoId": video_id,
                "Text": "train only token",
                "IsToxic": index % 2,
            }
        )
    rows.extend(
        [
            {
                "CommentId": "validation-row",
                "VideoId": next(iter(VALIDATION_VIDEO_IDS)),
                "Text": "validation leakage token",
                "IsToxic": 0,
            },
            {
                "CommentId": "test-row",
                "VideoId": next(iter(TEST_VIDEO_IDS)),
                "Text": "test leakage token",
                "IsToxic": 1,
            },
        ]
    )
    dataset = prepare_dataset(pd.DataFrame(rows))

    model = fit_on_train(dataset, calibrate=False)

    vocabulary = model.named_steps["tfidf"].vocabulary_
    assert "train" in vocabulary
    assert "validation" not in vocabulary
    assert "test" not in vocabulary
    assert "leakage" not in vocabulary


def test_fit_on_train_calibrates_only_the_train_rows():
    rows = []
    for index in range(10):
        rows.append(
            {
                "CommentId": f"train-{index}",
                "VideoId": next(iter(TRAIN_VIDEO_IDS)),
                "Text": f"train token {index}",
                "IsToxic": index % 2,
            }
        )
    dataset = prepare_dataset(pd.DataFrame(rows))

    model = fit_on_train(dataset, calibrate=True)

    calibrated = model.named_steps["classifier"]
    assert len(calibrated.calibrated_classifiers_) == 5
    assert all(estimator.estimator.classes_.tolist() == [False, True] for estimator in calibrated.calibrated_classifiers_)

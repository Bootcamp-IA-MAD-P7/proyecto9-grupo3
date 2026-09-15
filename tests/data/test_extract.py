import os
from pathlib import Path
import subprocess
import sys

import pandas as pd
import pytest

from src.moderation.data.extract import extract_dataset


@pytest.fixture
def valid_dataset() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "CommentId": ["comment-1"],
            "VideoId": ["video-1"],
            "Text": ["Synthetic test comment"],
            "IsToxic": [False],
        }
    )


def test_extracts_valid_dataset(tmp_path, valid_dataset):
    path = tmp_path / "dataset.csv"
    valid_dataset.to_csv(path, index=False)

    result = extract_dataset(path)

    assert len(result) == 1
    assert set(result.columns) == set(valid_dataset.columns)


def test_rejects_missing_file(tmp_path):
    with pytest.raises(FileNotFoundError, match="Dataset not found"):
        extract_dataset(tmp_path / "missing.csv")


def test_rejects_missing_columns(tmp_path, valid_dataset):
    path = tmp_path / "dataset.csv"
    valid_dataset.drop(columns=["Text"]).to_csv(path, index=False)

    with pytest.raises(ValueError, match="Missing required columns"):
        extract_dataset(path)


def test_rejects_blank_text(tmp_path, valid_dataset):
    path = tmp_path / "dataset.csv"
    valid_dataset.loc[0, "Text"] = "   "
    valid_dataset.to_csv(path, index=False)

    with pytest.raises(ValueError, match="Text contains 1 invalid rows"):
        extract_dataset(path)


def test_rejects_invalid_target(tmp_path, valid_dataset):
    path = tmp_path / "dataset.csv"

    invalid_dataset = valid_dataset.assign(IsToxic=[2])
    invalid_dataset.to_csv(path, index=False)

    with pytest.raises(
        ValueError,
        match="IsToxic contains 1 invalid rows",
    ):
        extract_dataset(path)


def test_rejects_empty_dataset(tmp_path, valid_dataset):
    path = tmp_path / "dataset.csv"
    valid_dataset.iloc[0:0].to_csv(path, index=False)

    with pytest.raises(ValueError, match="Dataset contains no rows"):
        extract_dataset(path)


def test_preserves_row_order(tmp_path, valid_dataset):
    path = tmp_path / "dataset.csv"
    dataset = pd.concat([valid_dataset] * 3, ignore_index=True)
    dataset["CommentId"] = ["comment-3", "comment-1", "comment-2"]
    dataset.to_csv(path, index=False)

    result = extract_dataset(path)

    assert result["CommentId"].tolist() == dataset["CommentId"].tolist()


def test_rejects_null_text(tmp_path, valid_dataset):
    path = tmp_path / "dataset.csv"
    valid_dataset.assign(Text=[None]).to_csv(path, index=False)

    with pytest.raises(ValueError, match="Text contains 1 invalid rows"):
        extract_dataset(path)


def test_cli_outputs_metadata_without_comment_text(tmp_path, valid_dataset):
    path = tmp_path / "dataset.csv"
    marker = "SYNTHETIC_COMMENT_MUST_NOT_APPEAR"
    valid_dataset.assign(Text=[marker]).to_csv(path, index=False)
    script = Path(__file__).resolve().parents[2] / "src/moderation/data/extract.py"
    environment = {**os.environ, "DATASET_PATH": str(path)}

    result = subprocess.run(
        [sys.executable, str(script)],
        env=environment,
        capture_output=True,
        text=True,
        timeout=30,
        check=True,
    )

    assert "Rows: 1" in result.stdout
    assert "Columns: 4" in result.stdout
    assert "IsToxic distribution:" in result.stdout
    assert marker not in result.stdout + result.stderr

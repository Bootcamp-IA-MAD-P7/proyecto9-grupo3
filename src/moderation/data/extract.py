import os
from pathlib import Path

import pandas as pd


REQUIRED_COLUMNS = {
    "CommentId",
    "VideoId",
    "Text",
    "IsToxic",
}


def validate_dataset(dataset: pd.DataFrame) -> None:
    """Validate the minimum dataset contract."""

    if dataset.empty:
        raise ValueError("Dataset contains no rows")

    missing_columns = REQUIRED_COLUMNS - set(dataset.columns)
    if missing_columns:
        raise ValueError(
            f"Missing required columns: {sorted(missing_columns)}"
        )

    invalid_text = (
        dataset["Text"].isna()
        | dataset["Text"].astype("string").str.strip().eq("")
    )

    if invalid_text.any():
        raise ValueError(
            f"Text contains {int(invalid_text.sum())} invalid rows"
        )

    invalid_target = (
        dataset["IsToxic"].isna()
        | ~dataset["IsToxic"].isin([0, 1, False, True])
    )

    if invalid_target.any():
        raise ValueError(
            f"IsToxic contains {int(invalid_target.sum())} invalid rows"
        )


def extract_dataset(path: str | Path) -> pd.DataFrame:
    """Load and validate the dataset from a local CSV file."""
    dataset_path = Path(path)

    if not dataset_path.is_file():
        raise FileNotFoundError(f"Dataset not found: {dataset_path}")

    dataset = pd.read_csv(dataset_path)
    validate_dataset(dataset)

    return dataset


if __name__ == "__main__":
    dataset_path = os.getenv("DATASET_PATH")

    if not dataset_path:
        raise RuntimeError("DATASET_PATH is not configured")

    dataset = extract_dataset(dataset_path)

    print(f"Rows: {len(dataset)}")
    print(f"Columns: {len(dataset.columns)}")
    print(f"Column names: {dataset.columns.tolist()}")
    print("IsToxic distribution:")
    print(dataset["IsToxic"].value_counts().sort_index())
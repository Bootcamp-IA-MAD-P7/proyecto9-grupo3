"""Create the shared grouped split used by every ensemble model."""

from pathlib import Path

import pandas as pd

from src.moderation.data.extract import extract_dataset


VIDEO_SPLITS = {
    "train": [
        "8HB18hZrhXc",
        "9pr1oE34bIM",
        "cT14IbTDW2c",
        "dDbRyFIkNII",
        "dG7mZQvaQDk",
    ],
    "validation": [
        "04kJtp6pVXI",
        "4rCweDxDqdw",
        "XRuCW80L9mA",
    ],
    "test": [
        "5vF4si3hoRA",
        "Dt9-byUhPdg",
        "TZxEyoplYbI",
        "bUgKZMSxr3E",
    ],
}

EXPECTED_COUNTS = {
    "train": {"rows": 580, "toxic": 246},
    "validation": {"rows": 219, "toxic": 123},
    "test": {"rows": 185, "toxic": 88},
}


def create_split_manifest(dataset: pd.DataFrame) -> pd.DataFrame:
    """Assign known videos to the agreed train, validation, and test sets."""
    if dataset["CommentId"].duplicated().any():
        raise ValueError("CommentId must be unique")

    video_to_split = {
        video_id: split
        for split, video_ids in VIDEO_SPLITS.items()
        for video_id in video_ids
    }

    known_videos = dataset["VideoId"].ne("#NAME?")
    manifest = dataset.loc[
        known_videos,
        ["CommentId", "VideoId", "IsToxic"],
    ].copy()
    manifest["split"] = manifest["VideoId"].map(video_to_split)

    if manifest["split"].isna().any():
        missing_videos = sorted(
            manifest.loc[manifest["split"].isna(), "VideoId"].unique()
        )
        raise ValueError(f"Videos without split: {missing_videos}")

    for split, expected in EXPECTED_COUNTS.items():
        split_rows = manifest.loc[manifest["split"].eq(split)]
        observed_rows = len(split_rows)
        observed_toxic = int(split_rows["IsToxic"].sum())

        if observed_rows != expected["rows"]:
            raise ValueError(
                f"{split}: expected {expected['rows']} rows, "
                f"found {observed_rows}"
            )

        if observed_toxic != expected["toxic"]:
            raise ValueError(
                f"{split}: expected {expected['toxic']} toxic rows, "
                f"found {observed_toxic}"
            )

    return manifest[["CommentId", "VideoId", "split"]]


def main() -> None:
    """Load the local dataset and write the reviewable split manifest."""
    dataset_path = Path("data/raw/youtoxic_english_1000.csv")
    output_path = Path("data/splits/common_split.csv")

    dataset = extract_dataset(dataset_path)
    manifest = create_split_manifest(dataset)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    manifest.to_csv(output_path, index=False)

    summary = (
        dataset.merge(manifest, on=["CommentId", "VideoId"])
        .groupby("split")
        .agg(
            comments=("CommentId", "size"),
            toxic=("IsToxic", "sum"),
            toxic_percentage=("IsToxic", lambda values: values.mean() * 100),
        )
    )

    unknown_count = int(dataset["VideoId"].eq("#NAME?").sum())

    print(summary.round(1))
    print(f"\nExcluded #NAME? rows: {unknown_count}")
    print(f"Manifest written to: {output_path}")


if __name__ == "__main__":
    main()

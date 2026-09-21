"""Compare aligned validation probabilities from the three candidate models."""

import argparse
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.moderation.models.comparison import compare_prediction_files


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--logistic", type=Path, required=True)
    parser.add_argument("--svm", type=Path, required=True)
    parser.add_argument("--transformer", type=Path, required=True)
    parser.add_argument(
        "--split",
        type=Path,
        default=Path("data/splits/common_split.csv"),
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("data/local/model_comparison"),
    )
    parser.add_argument("--target-recall", type=float, default=0.8)
    return parser.parse_args()


if __name__ == "__main__":
    arguments = parse_args()
    report = compare_prediction_files(
        {
            "logistic": arguments.logistic,
            "svm": arguments.svm,
            "transformer": arguments.transformer,
        },
        arguments.output,
        split_path=arguments.split,
        target_recall=arguments.target_recall,
    )
    for name, metrics in report["models"].items():
        print(
            f"{name}: PR-AUC={metrics['pr_auc']:.4f}, "
            f"F1={metrics['f1']:.4f}, recall={metrics['recall']:.4f}, "
            f"Brier={metrics['brier_score']:.4f}"
        )

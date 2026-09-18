"""Run Arnaldo's reproducible TF-IDF + logistic regression baseline."""

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.moderation.models.logistic_tfidf import run_training


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset", type=Path, required=True, help="Local raw CSV path")
    parser.add_argument(
        "--split", type=Path, default=Path("data/splits/common_split.csv"),
        help="Shared CommentId/VideoId/split manifest",
    )
    parser.add_argument(
        "--output-dir", type=Path, default=Path("data/local/logistic_tfidf"),
        help="Local directory for model, metrics and predictions",
    )
    parser.add_argument(
        "--final-test", action="store_true",
        help="Evaluate the held-out test only after model decisions are fixed",
    )
    args = parser.parse_args()
    report = run_training(args.dataset, args.split, args.output_dir, final_test=args.final_test)
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()

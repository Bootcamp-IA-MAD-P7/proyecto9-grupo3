"""Run Arnaldo's reproducible TF-IDF + logistic regression baseline."""

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.moderation.models.logistic_tfidf import run_training
from src.moderation.models.final_test_gate import (
    verify_committed_config,
    write_prediction_metadata,
)


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
    parser.add_argument("--ensemble-config", type=Path)
    args = parser.parse_args()
    if args.final_test and args.ensemble_config is None:
        parser.error("--final-test requires --ensemble-config")
    if args.final_test:
        config_sha256 = verify_committed_config(args.ensemble_config, args.split)
    report = run_training(
        args.dataset,
        args.split,
        args.output_dir,
        final_test=args.final_test,
        ensemble_config=args.ensemble_config,
    )
    write_prediction_metadata(
        args.output_dir / "validation_predictions.csv",
        model_name="logistic",
        split="validation",
        manifest_path=args.split,
    )
    if args.final_test:
        write_prediction_metadata(
            args.output_dir / "test_predictions.csv",
            model_name="logistic",
            split="test",
            manifest_path=args.split,
            config_sha256=config_sha256,
        )
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()

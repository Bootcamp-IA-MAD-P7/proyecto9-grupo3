"""Train the calibrated SVM without evaluating test by default."""

import argparse
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.moderation.modeling.svm_baseline import run_baseline
from src.moderation.models.final_test_gate import (
    verify_committed_config,
    write_prediction_metadata,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--dataset",
        type=Path,
        default=Path("data/raw/youtoxic_english_1000.csv"),
    )
    parser.add_argument(
        "--split",
        type=Path,
        default=Path("data/splits/common_split.csv"),
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("data/local/svm_tfidf"),
    )
    parser.add_argument("--final-test", action="store_true")
    parser.add_argument("--ensemble-config", type=Path)
    arguments = parser.parse_args()
    if arguments.final_test and arguments.ensemble_config is None:
        parser.error("--final-test requires --ensemble-config")
    return arguments


if __name__ == "__main__":
    arguments = parse_args()
    if arguments.final_test:
        config_sha256 = verify_committed_config(arguments.ensemble_config, arguments.split)
    report = run_baseline(
        arguments.dataset,
        arguments.split,
        arguments.output,
        final_test=arguments.final_test,
        ensemble_config=arguments.ensemble_config,
    )
    write_prediction_metadata(
        report["validation_output_path"],
        model_name="svm",
        split="validation",
        manifest_path=arguments.split,
    )
    if arguments.final_test:
        write_prediction_metadata(
            report["test_output_path"],
            model_name="svm",
            split="test",
            manifest_path=arguments.split,
            config_sha256=config_sha256,
        )
    print(f"Validation metrics: {report['validation_metrics']}")
    print(f"Selected threshold: {report['threshold']:.6f}")
    if "test" not in report:
        print("Test remains sealed. Use --final-test only after the ensemble is fixed.")

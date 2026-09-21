"""Fit or finally evaluate the frozen weighted soft-voting ensemble."""

import argparse
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.moderation.models.ensemble import (
    evaluate_frozen_ensemble_from_files,
    fit_ensemble_from_files,
)


def add_component_paths(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--logistic", type=Path, required=True)
    parser.add_argument("--svm", type=Path, required=True)
    parser.add_argument("--transformer", type=Path, required=True)
    parser.add_argument(
        "--split",
        type=Path,
        default=Path("data/splits/common_split.csv"),
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)

    fit = commands.add_parser("fit", help="Freeze weights and threshold on validation")
    add_component_paths(fit)
    fit.add_argument("--logistic-weight", type=float, default=0.1)
    fit.add_argument("--svm-weight", type=float, default=0.0)
    fit.add_argument("--transformer-weight", type=float, default=0.9)
    fit.add_argument("--target-recall", type=float, default=0.8)
    fit.add_argument("--output", type=Path, default=Path("data/local/ensemble"))
    fit.add_argument("--config", type=Path, default=Path("configs/ensemble.json"))

    final_test = commands.add_parser(
        "final-test", help="Apply a frozen config once to held-out test predictions"
    )
    add_component_paths(final_test)
    final_test.add_argument(
        "--config", type=Path, default=Path("configs/ensemble.json")
    )
    final_test.add_argument(
        "--output", type=Path, default=Path("data/local/ensemble_final")
    )
    return parser.parse_args()


if __name__ == "__main__":
    arguments = parse_args()
    paths = {
        "logistic": arguments.logistic,
        "svm": arguments.svm,
        "transformer": arguments.transformer,
    }
    if arguments.command == "fit":
        report = fit_ensemble_from_files(
            paths,
            split_path=arguments.split,
            output_path=arguments.output,
            config_path=arguments.config,
            weights={
                "logistic": arguments.logistic_weight,
                "svm": arguments.svm_weight,
                "transformer": arguments.transformer_weight,
            },
            target_recall=arguments.target_recall,
        )
        print(json.dumps(report, indent=2))
        print("Test remains sealed. Commit the config before final-test.")
    else:
        report = evaluate_frozen_ensemble_from_files(
            paths,
            split_path=arguments.split,
            config_path=arguments.config,
            output_path=arguments.output,
        )
        print(json.dumps(report, indent=2))

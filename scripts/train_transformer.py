"""Train the lightweight transformer without evaluating test by default."""

import argparse
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.moderation.models.transformer import (
    DEFAULT_EARLY_STOPPING_PATIENCE,
    DEFAULT_MODEL_REVISION,
    DEFAULT_WEIGHT_DECAY,
    run_transformer,
)
from src.moderation.models.final_test_gate import (
    verify_committed_config,
    write_prediction_metadata,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
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
        default=Path("data/local/transformer"),
    )
    parser.add_argument("--model-name", default="distilbert-base-uncased")
    parser.add_argument("--model-revision", default=DEFAULT_MODEL_REVISION)
    parser.add_argument("--epochs", type=int, default=3)
    parser.add_argument("--batch-size", type=int, default=16)
    parser.add_argument("--max-length", type=int, default=128)
    parser.add_argument("--learning-rate", type=float, default=2e-5)
    parser.add_argument("--weight-decay", type=float, default=DEFAULT_WEIGHT_DECAY)
    parser.add_argument(
        "--early-stopping-patience",
        type=int,
        default=DEFAULT_EARLY_STOPPING_PATIENCE,
    )
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--final-test", action="store_true")
    parser.add_argument("--ensemble-config", type=Path)
    arguments = parser.parse_args()
    if arguments.final_test and arguments.ensemble_config is None:
        parser.error("--final-test requires --ensemble-config")
    return arguments


if __name__ == "__main__":
    arguments = parse_args()
    if not arguments.dataset.is_file():
        raise SystemExit(
            f"Dataset not found: {arguments.dataset}\n"
            "Provide a local CSV with --dataset PATH. The expected default is "
            "data/raw/youtoxic_english_1000.csv; an authorized copy may use an "
            "alternative filename such as "
            "data/raw/youtoxic_english_1000 (1).csv."
        )
    if arguments.final_test:
        config_sha256 = verify_committed_config(arguments.ensemble_config, arguments.split)
    report = run_transformer(
        arguments.dataset,
        arguments.split,
        arguments.output,
        model_name=arguments.model_name,
        model_revision=arguments.model_revision,
        epochs=arguments.epochs,
        batch_size=arguments.batch_size,
        max_length=arguments.max_length,
        learning_rate=arguments.learning_rate,
        weight_decay=arguments.weight_decay,
        early_stopping_patience=arguments.early_stopping_patience,
        seed=arguments.seed,
        final_test=arguments.final_test,
        ensemble_config=arguments.ensemble_config,
    )
    write_prediction_metadata(
        arguments.output / "validation_predictions.csv",
        model_name="transformer",
        split="validation",
        manifest_path=arguments.split,
    )
    if arguments.final_test:
        write_prediction_metadata(
            arguments.output / "test_predictions.csv",
            model_name="transformer",
            split="test",
            manifest_path=arguments.split,
            config_sha256=config_sha256,
        )
    print(f"Validation metrics: {report['validation']}")
    print(f"Selected threshold: {report['threshold']:.6f}")
    if "test" not in report:
        print("Test remains sealed. Use --final-test only after the ensemble is fixed.")

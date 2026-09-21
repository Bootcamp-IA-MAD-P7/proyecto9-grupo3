"""Train the lightweight transformer without evaluating test by default."""

import argparse
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.moderation.models.transformer import DEFAULT_MODEL_REVISION, run_transformer


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
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--final-test", action="store_true")
    return parser.parse_args()


if __name__ == "__main__":
    arguments = parse_args()
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
        seed=arguments.seed,
        final_test=arguments.final_test,
    )
    print(f"Validation metrics: {report['validation']}")
    print(f"Selected threshold: {report['threshold']:.6f}")
    if "test" not in report:
        print("Test remains sealed. Use --final-test only after the ensemble is fixed.")

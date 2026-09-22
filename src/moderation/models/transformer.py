"""Leakage-safe helpers for the lightweight transformer toxicity model."""

from __future__ import annotations

from collections.abc import Sequence
from importlib.metadata import version
import json
from pathlib import Path
import platform
import random

import numpy as np
import pandas as pd
import torch
from sklearn.metrics import (
    average_precision_score,
    brier_score_loss,
    confusion_matrix,
    f1_score,
    precision_score,
    recall_score,
)
from torch.optim import AdamW
from torch.utils.data import DataLoader, Dataset
from transformers import AutoModelForSequenceClassification, AutoTokenizer

from src.moderation.models.logistic_tfidf import load_partitions, select_threshold


PREDICTION_COLUMNS = ["CommentId", "IsToxic", "probability", "prediction"]
DEFAULT_MODEL_REVISION = "12040accade4e8a0f71eabdb258fecc2e7e948be"


class ToxicityDataset(Dataset):
    """Tokenized texts and binary labels, excluding every metadata label."""

    def __init__(self, partition: pd.DataFrame, tokenizer, *, max_length: int = 128):
        texts = partition["Text"].astype("string").str.strip().tolist()
        self.encodings = tokenizer(
            texts,
            truncation=True,
            padding="max_length",
            max_length=max_length,
            return_tensors="pt",
        )
        labels = partition["IsToxic"].astype(int).to_numpy(copy=True)
        self.labels = torch.as_tensor(labels, dtype=torch.long)

    def __len__(self) -> int:
        return len(self.labels)

    def __getitem__(self, index: int) -> dict[str, torch.Tensor]:
        item = {name: values[index] for name, values in self.encodings.items()}
        item["labels"] = self.labels[index]
        return item


def build_prediction_frame(
    partition: pd.DataFrame,
    probabilities: Sequence[float] | np.ndarray,
    *,
    threshold: float,
) -> pd.DataFrame:
    """Return probabilities and decisions without changing row alignment."""
    probability = np.asarray(probabilities, dtype=float)
    if len(probability) != len(partition) or not np.isfinite(probability).all():
        raise ValueError("Probability vector must match the partition")
    if ((probability < 0) | (probability > 1)).any():
        raise ValueError("All probabilities must be between zero and one")
    return pd.DataFrame(
        {
            "CommentId": partition["CommentId"].to_numpy(),
            "IsToxic": partition["IsToxic"].astype(int).to_numpy(),
            "probability": probability,
            "prediction": (probability >= threshold).astype(int),
        }
    )


def summarize_predictions(predictions: pd.DataFrame) -> dict[str, object]:
    """Calculate the metrics shared by all three candidate models."""
    actual = predictions["IsToxic"].astype(int)
    predicted = predictions["prediction"].astype(int)
    probability = predictions["probability"].astype(float)
    return {
        "precision": float(precision_score(actual, predicted, zero_division=0)),
        "recall": float(recall_score(actual, predicted, zero_division=0)),
        "f1": float(f1_score(actual, predicted, zero_division=0)),
        "confusion_matrix": confusion_matrix(actual, predicted, labels=[0, 1]).tolist(),
        "pr_auc": float(average_precision_score(actual, probability)),
        "brier_score": float(brier_score_loss(actual, probability)),
    }


def train_model(
    model,
    dataset: Dataset,
    *,
    epochs: int,
    batch_size: int,
    learning_rate: float,
    device: torch.device,
) -> list[float]:
    """Fine-tune a sequence classifier and return mean loss per epoch."""
    model.to(device)
    optimizer = AdamW(model.parameters(), lr=learning_rate)
    loader = DataLoader(dataset, batch_size=batch_size, shuffle=True)
    history = []
    for _ in range(epochs):
        model.train()
        losses = []
        for batch in loader:
            optimizer.zero_grad()
            inputs = {name: value.to(device) for name, value in batch.items()}
            output = model(**inputs)
            output.loss.backward()
            optimizer.step()
            losses.append(float(output.loss.detach().cpu()))
        history.append(float(np.mean(losses)))
    return history


def predict_probabilities(
    model,
    dataset: Dataset,
    *,
    batch_size: int,
    device: torch.device,
) -> np.ndarray:
    """Return positive-class probabilities in dataset order."""
    model.to(device)
    model.eval()
    loader = DataLoader(dataset, batch_size=batch_size, shuffle=False)
    probabilities = []
    with torch.no_grad():
        for batch in loader:
            inputs = {
                name: value.to(device)
                for name, value in batch.items()
                if name != "labels"
            }
            logits = model(**inputs).logits
            probabilities.extend(torch.softmax(logits, dim=1)[:, 1].cpu().tolist())
    return np.asarray(probabilities, dtype=float)


def _set_seed(seed: int) -> None:
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    torch.use_deterministic_algorithms(True)
    torch.backends.cudnn.deterministic = True
    torch.backends.cudnn.benchmark = False
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(seed)


def run_transformer(
    dataset_path: str | Path,
    split_path: str | Path,
    output_path: str | Path,
    *,
    model_name: str = "distilbert-base-uncased",
    model_revision: str = DEFAULT_MODEL_REVISION,
    epochs: int = 3,
    batch_size: int = 16,
    max_length: int = 128,
    learning_rate: float = 2e-5,
    seed: int = 42,
    target_recall: float = 0.8,
    final_test: bool = False,
    ensemble_config: str | Path | None = None,
) -> dict[str, object]:
    """Train on the common train split and evaluate without opening test by default."""
    if final_test:
        if ensemble_config is None:
            raise ValueError("final_test requires a frozen ensemble_config")
        from src.moderation.models.final_test_gate import verify_committed_config
        verify_committed_config(ensemble_config, split_path)
    _set_seed(seed)
    output = Path(output_path)
    output.mkdir(parents=True, exist_ok=True)
    if not final_test and (output / "test_predictions.csv").exists():
        raise ValueError(
            "Output directory contains stale test_predictions.csv; use a clean "
            "validation directory or explicitly request --final-test"
        )
    partitions = load_partitions(dataset_path, split_path)
    tokenizer = AutoTokenizer.from_pretrained(model_name, revision=model_revision)
    model = AutoModelForSequenceClassification.from_pretrained(
        model_name,
        num_labels=2,
        revision=model_revision,
    )
    train_dataset = ToxicityDataset(partitions["train"], tokenizer, max_length=max_length)
    validation_dataset = ToxicityDataset(
        partitions["validation"], tokenizer, max_length=max_length
    )
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    loss_history = train_model(
        model,
        train_dataset,
        epochs=epochs,
        batch_size=batch_size,
        learning_rate=learning_rate,
        device=device,
    )
    validation_probability = predict_probabilities(
        model,
        validation_dataset,
        batch_size=batch_size,
        device=device,
    )
    validation_actual = partitions["validation"]["IsToxic"].astype(int).to_numpy()
    threshold = select_threshold(
        validation_actual,
        validation_probability,
        target_recall=target_recall,
    )
    validation_predictions = build_prediction_frame(
        partitions["validation"], validation_probability, threshold=threshold
    )
    validation_metrics = summarize_predictions(validation_predictions)
    validation_predictions.to_csv(output / "validation_predictions.csv", index=False)

    train_probability = predict_probabilities(
        model,
        train_dataset,
        batch_size=batch_size,
        device=device,
    )
    train_predictions = build_prediction_frame(
        partitions["train"], train_probability, threshold=threshold
    )
    train_metrics = summarize_predictions(train_predictions)

    model_output = output / "model"
    model.save_pretrained(model_output)
    tokenizer.save_pretrained(model_output)
    report: dict[str, object] = {
        "model_name": model_name,
        "model_revision": model_revision,
        "seed": seed,
        "epochs": epochs,
        "batch_size": batch_size,
        "max_length": max_length,
        "learning_rate": learning_rate,
        "device": str(device),
        "train_loss": loss_history,
        "threshold": threshold,
        "target_recall": target_recall,
        "runtime_versions": {
            "python": platform.python_version(),
            "numpy": version("numpy"),
            "pandas": version("pandas"),
            "scikit-learn": version("scikit-learn"),
            "torch": version("torch"),
            "transformers": version("transformers"),
        },
        "train": train_metrics,
        "validation": validation_metrics,
    }
    if final_test:
        test_dataset = ToxicityDataset(partitions["test"], tokenizer, max_length=max_length)
        test_probability = predict_probabilities(
            model,
            test_dataset,
            batch_size=batch_size,
            device=device,
        )
        test_predictions = build_prediction_frame(
            partitions["test"], test_probability, threshold=threshold
        )
        test_predictions.to_csv(output / "test_predictions.csv", index=False)
        report["test"] = summarize_predictions(test_predictions)
    (output / "metrics.json").write_text(
        json.dumps(report, indent=2) + "\n", encoding="utf-8"
    )
    return report

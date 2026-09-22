import pandas as pd
import pytest
import torch
from types import SimpleNamespace

from src.moderation.models.transformer import (
    ToxicityDataset,
    _set_seed,
    build_prediction_frame,
    predict_probabilities,
    run_transformer,
    summarize_predictions,
    train_model,
)


class RecordingTokenizer:
    def __init__(self):
        self.texts = None
        self.options = None

    def __call__(self, texts, **options):
        self.texts = texts
        self.options = options
        return {
            "input_ids": torch.tensor([[1, 2], [3, 0]]),
            "attention_mask": torch.tensor([[1, 1], [1, 0]]),
        }


def test_seed_enables_deterministic_torch_algorithms():
    _set_seed(42)

    assert torch.are_deterministic_algorithms_enabled()
    assert torch.backends.cudnn.deterministic
    assert not torch.backends.cudnn.benchmark


def test_dataset_strips_text_and_never_exposes_secondary_labels():
    tokenizer = RecordingTokenizer()
    partition = pd.DataFrame(
        {
            "CommentId": ["a", "b"],
            "Text": ["  first comment  ", "second comment"],
            "IsToxic": [0, 1],
            "IsAbusive": [1, 1],
        }
    )

    dataset = ToxicityDataset(partition, tokenizer, max_length=32)

    assert tokenizer.texts == ["first comment", "second comment"]
    assert tokenizer.options == {
        "truncation": True,
        "padding": "max_length",
        "max_length": 32,
        "return_tensors": "pt",
    }
    assert set(dataset[1]) == {"input_ids", "attention_mask", "labels"}
    assert dataset[1]["labels"].item() == 1


def test_prediction_frame_preserves_alignment_and_applies_threshold():
    partition = pd.DataFrame(
        {
            "CommentId": ["comment-2", "comment-1"],
            "Text": ["two", "one"],
            "IsToxic": [1, 0],
        }
    )

    predictions = build_prediction_frame(partition, [0.8, 0.4], threshold=0.5)

    assert predictions.to_dict("list") == {
        "CommentId": ["comment-2", "comment-1"],
        "IsToxic": [1, 0],
        "probability": [0.8, 0.4],
        "prediction": [1, 0],
    }


@pytest.mark.parametrize("probabilities", [[0.5], [-0.1, 0.2], [0.2, 1.1]])
def test_prediction_frame_rejects_invalid_probability_vectors(probabilities):
    partition = pd.DataFrame(
        {"CommentId": ["a", "b"], "Text": ["one", "two"], "IsToxic": [0, 1]}
    )

    with pytest.raises(ValueError, match="(?i)probabilit"):
        build_prediction_frame(partition, probabilities, threshold=0.5)


def test_prediction_metrics_include_classification_ranking_and_calibration():
    predictions = pd.DataFrame(
        {
            "CommentId": ["a", "b", "c", "d"],
            "IsToxic": [0, 1, 1, 0],
            "probability": [0.1, 0.8, 0.4, 0.7],
            "prediction": [0, 1, 0, 1],
        }
    )

    metrics = summarize_predictions(predictions)

    assert metrics["precision"] == pytest.approx(0.5)
    assert metrics["recall"] == pytest.approx(0.5)
    assert metrics["f1"] == pytest.approx(0.5)
    assert metrics["confusion_matrix"] == [[1, 1], [1, 1]]
    assert metrics["pr_auc"] == pytest.approx(5 / 6)
    assert metrics["brier_score"] == pytest.approx(0.225)


class TinyClassifier(torch.nn.Module):
    def __init__(self):
        super().__init__()
        self.classifier = torch.nn.Linear(2, 2)

    def forward(self, input_ids, attention_mask, labels=None):
        logits = self.classifier(input_ids.float() * attention_mask.float())
        loss = None if labels is None else torch.nn.functional.cross_entropy(logits, labels)
        return SimpleNamespace(logits=logits, loss=loss)


class TensorDataset(torch.utils.data.Dataset):
    def __init__(self):
        self.rows = [
            {"input_ids": torch.tensor([1, 0]), "attention_mask": torch.tensor([1, 0]), "labels": torch.tensor(0)},
            {"input_ids": torch.tensor([0, 1]), "attention_mask": torch.tensor([0, 1]), "labels": torch.tensor(1)},
        ]

    def __len__(self):
        return len(self.rows)

    def __getitem__(self, index):
        return self.rows[index]


def test_training_and_prediction_use_real_torch_batches():
    torch.manual_seed(42)
    model = TinyClassifier()
    dataset = TensorDataset()
    before = model.classifier.weight.detach().clone()

    history = train_model(
        model,
        dataset,
        epochs=2,
        batch_size=2,
        learning_rate=0.1,
        device=torch.device("cpu"),
    )
    probabilities = predict_probabilities(
        model,
        dataset,
        batch_size=2,
        device=torch.device("cpu"),
    )

    assert len(history) == 2
    assert all(loss >= 0 for loss in history)
    assert not torch.equal(before, model.classifier.weight.detach())
    assert probabilities.shape == (2,)
    assert ((probabilities >= 0) & (probabilities <= 1)).all()


def test_run_transformer_keeps_test_sealed_by_default(tmp_path, monkeypatch):
    rows = []
    split_rows = []
    definitions = [
        ("train", "train-video", 4),
        ("validation", "validation-video", 2),
        ("test", "test-video", 1),
    ]
    for split, video, count in definitions:
        for index in range(count):
            comment_id = f"{split}-{index}"
            rows.append(
                {
                    "CommentId": comment_id,
                    "VideoId": video,
                    "Text": f" {split} text {index} ",
                    "IsToxic": index % 2,
                    "IsAbusive": 1,
                }
            )
            split_rows.append({"CommentId": comment_id, "VideoId": video, "split": split})
    dataset_path = tmp_path / "dataset.csv"
    split_path = tmp_path / "split.csv"
    output_path = tmp_path / "output"
    pd.DataFrame(rows).to_csv(dataset_path, index=False)
    pd.DataFrame(split_rows).to_csv(split_path, index=False)

    class Saveable:
        def save_pretrained(self, path):
            path.mkdir(parents=True, exist_ok=True)
            (path / "saved.txt").write_text("saved", encoding="utf-8")

    fake_tokenizer = Saveable()
    fake_model = Saveable()
    monkeypatch.setattr(
        "src.moderation.models.transformer.AutoTokenizer.from_pretrained",
        lambda _, revision: fake_tokenizer,
    )
    monkeypatch.setattr(
        "src.moderation.models.transformer.AutoModelForSequenceClassification.from_pretrained",
        lambda _, num_labels, revision: fake_model,
    )
    monkeypatch.setattr("src.moderation.models.transformer.ToxicityDataset", lambda frame, tokenizer, max_length: frame)
    monkeypatch.setattr("src.moderation.models.transformer.train_model", lambda *args, **kwargs: [0.5])

    prediction_calls = []

    def validation_only(model, dataset, **kwargs):
        prediction_calls.append(len(dataset))
        if len(dataset) == 4:
            return torch.tensor([0.1, 0.2, 0.8, 0.9]).numpy()
        if len(dataset) == 2:
            return torch.tensor([0.2, 0.8]).numpy()
        raise AssertionError("test split was evaluated")

    monkeypatch.setattr("src.moderation.models.transformer.predict_probabilities", validation_only)

    report = run_transformer(dataset_path, split_path, output_path, epochs=1)

    assert set(report) >= {"train", "validation", "threshold"}
    assert set(report["train"]) == {
        "precision",
        "recall",
        "f1",
        "confusion_matrix",
        "pr_auc",
        "brier_score",
    }
    assert report["validation"]["recall"] == 1.0
    assert report["threshold"] == pytest.approx(0.8)
    assert prediction_calls == [2, 4]
    assert report["model_revision"] == "12040accade4e8a0f71eabdb258fecc2e7e948be"
    assert set(report["runtime_versions"]) == {
        "python",
        "numpy",
        "pandas",
        "scikit-learn",
        "torch",
        "transformers",
    }
    assert (output_path / "validation_predictions.csv").exists()
    assert (output_path / "metrics.json").exists()
    assert (output_path / "model" / "saved.txt").exists()
    assert not (output_path / "test_predictions.csv").exists()


def test_default_run_rejects_output_directory_with_stale_test_predictions(tmp_path):
    output_path = tmp_path / "output"
    output_path.mkdir()
    (output_path / "test_predictions.csv").write_text("sensitive", encoding="utf-8")

    with pytest.raises(ValueError, match="stale test_predictions"):
        run_transformer(
            tmp_path / "missing-dataset.csv",
            tmp_path / "missing-split.csv",
            output_path,
        )

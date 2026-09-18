"""Contract tests for Arnaldo's text-only baseline."""

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

import joblib
import pandas as pd

from src.moderation.models.logistic_tfidf import run_training


class LogisticTfidfTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.root = Path(self.directory.name)
        self.dataset_path = self.root / "raw.csv"
        self.manifest_path = self.root / "split.csv"
        self.output_dir = self.root / "output"
        rows = [
            ("t1", "train-a", "  bad insult  ", 1, "train"),
            ("t2", "train-a", "kind helpful", 0, "train"),
            ("t3", "train-b", "bad rude", 1, "train"),
            ("t4", "train-b", "kind welcome", 0, "train"),
            ("v1", "validation-a", "validationonly bad", 1, "validation"),
            ("v2", "validation-a", "kind person", 0, "validation"),
            ("e1", "test-a", "testonly rude", 1, "test"),
            ("e2", "test-a", "welcome person", 0, "test"),
            ("x1", "#NAME?", "unknown source", 1, None),
        ]
        pd.DataFrame(
            rows,
            columns=["CommentId", "VideoId", "Text", "IsToxic", "split"],
        ).drop(columns="split").to_csv(self.dataset_path, index=False)
        pd.DataFrame(
            [row for row in rows if row[4] is not None],
            columns=["CommentId", "VideoId", "Text", "IsToxic", "split"],
        )[["CommentId", "VideoId", "split"]].to_csv(self.manifest_path, index=False)

    def test_training_uses_only_train_text_and_holds_back_test(self):
        run_training(self.dataset_path, self.manifest_path, self.output_dir)

        model = joblib.load(self.output_dir / "logistic_tfidf.joblib")
        vocabulary = model.named_steps["tfidf"].vocabulary_
        self.assertIn("bad", vocabulary)
        self.assertNotIn("validationonly", vocabulary)
        self.assertNotIn("testonly", vocabulary)
        self.assertTrue((self.output_dir / "validation_predictions.csv").exists())
        self.assertFalse((self.output_dir / "test_predictions.csv").exists())
        predictions = pd.read_csv(self.output_dir / "validation_predictions.csv")
        self.assertEqual(
            predictions.columns.tolist(),
            ["CommentId", "IsToxic", "probability", "prediction"],
        )
        self.assertEqual(predictions["CommentId"].tolist(), ["v1", "v2"])
        self.assertTrue(predictions["probability"].between(0, 1).all())
        report = json.loads((self.output_dir / "metrics.json").read_text(encoding="utf-8"))
        self.assertEqual(report["train_rows"], 4)
        self.assertEqual(report["validation_rows"], 2)
        self.assertEqual(report["excluded_unknown_video_rows"], 1)
        self.assertNotIn("test", report)
        self.assertEqual(
            set(report["validation"]),
            {"precision", "recall", "f1", "confusion_matrix", "pr_auc", "brier_score"},
        )

    def test_final_evaluation_exports_test_by_comment_id(self):
        run_training(self.dataset_path, self.manifest_path, self.output_dir, final_test=True)

        predictions = pd.read_csv(self.output_dir / "test_predictions.csv")
        self.assertEqual(predictions["CommentId"].tolist(), ["e1", "e2"])
        report = json.loads((self.output_dir / "metrics.json").read_text(encoding="utf-8"))
        self.assertIn("test", report)

    def test_rejects_manifest_video_mismatch(self):
        manifest = pd.read_csv(self.manifest_path)
        manifest.loc[0, "VideoId"] = "wrong-video"
        manifest.to_csv(self.manifest_path, index=False)

        with self.assertRaisesRegex(ValueError, "VideoId mismatch"):
            run_training(self.dataset_path, self.manifest_path, self.output_dir)

    def test_rejects_video_leak_across_splits(self):
        manifest = pd.read_csv(self.manifest_path)
        manifest.loc[manifest["split"].eq("validation"), "VideoId"] = "train-a"
        dataset = pd.read_csv(self.dataset_path)
        dataset.loc[dataset["CommentId"].isin(["v1", "v2"]), "VideoId"] = "train-a"
        manifest.to_csv(self.manifest_path, index=False)
        dataset.to_csv(self.dataset_path, index=False)

        with self.assertRaisesRegex(ValueError, "VideoId appears in multiple splits"):
            run_training(self.dataset_path, self.manifest_path, self.output_dir)

    def test_cli_keeps_comment_text_out_of_console_and_exports(self):
        script = Path(__file__).resolve().parents[2] / "scripts/train_logistic_tfidf.py"
        result = subprocess.run(
            [sys.executable, str(script), "--dataset", str(self.dataset_path),
             "--split", str(self.manifest_path), "--output-dir", str(self.output_dir)],
            capture_output=True, text=True, timeout=30,
        )

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertNotIn("validationonly bad", result.stdout + result.stderr)
        self.assertFalse((self.output_dir / "test_predictions.csv").exists())


if __name__ == "__main__":
    unittest.main()

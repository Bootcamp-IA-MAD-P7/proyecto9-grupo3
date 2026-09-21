"""Contract tests for Arnaldo's text-only baseline."""

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.dummy import DummyClassifier

from src.moderation.models.logistic_tfidf import (
    build_pipeline,
    evaluate,
    load_partitions,
    ranking_metrics,
    run_training,
    select_threshold,
)


class LogisticTfidfTests(unittest.TestCase):
    def test_pipeline_uses_balanced_character_ngrams(self):
        model = build_pipeline()

        vectorizer = model.named_steps["tfidf"]
        classifier = model.named_steps["logistic"]
        self.assertEqual(vectorizer.analyzer, "char_wb")
        self.assertEqual(vectorizer.ngram_range, (3, 5))
        self.assertEqual(vectorizer.min_df, 2)
        self.assertTrue(vectorizer.sublinear_tf)
        self.assertEqual(classifier.C, 3)
        self.assertEqual(classifier.class_weight, "balanced")

    def test_threshold_is_highest_value_that_reaches_target_recall(self):
        actual = np.array([1, 0, 1, 0])
        probabilities = np.array([0.9, 0.8, 0.4, 0.2])

        threshold = select_threshold(actual, probabilities, target_recall=0.8)

        self.assertEqual(threshold, 0.4)

    def test_ranking_metrics_report_review_capacity(self):
        actual = np.array([1, 0, 1, 0])
        probabilities = np.array([0.9, 0.8, 0.7, 0.1])

        metrics = ranking_metrics(actual, probabilities, review_sizes=(2, 3, 10))

        self.assertEqual(
            metrics,
            {
                "2": {"precision": 0.5, "recall": 0.5, "toxic_found": 1},
                "3": {"precision": 2 / 3, "recall": 1.0, "toxic_found": 2},
            },
        )

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
        self.assertEqual(report["target_recall"], 0.8)
        self.assertEqual(
            report["threshold_status"],
            "selected_on_validation_for_target_recall",
        )
        self.assertGreaterEqual(report["validation"]["recall"], 0.8)
        self.assertNotIn("test", report)
        self.assertEqual(
            set(report["validation"]),
            {
                "precision",
                "recall",
                "f1",
                "confusion_matrix",
                "pr_auc",
                "brier_score",
                "ranking",
            },
        )

    def test_final_evaluation_exports_test_by_comment_id(self):
        run_training(self.dataset_path, self.manifest_path, self.output_dir, final_test=True)

        predictions = pd.read_csv(self.output_dir / "test_predictions.csv")
        self.assertEqual(predictions["CommentId"].tolist(), ["e1", "e2"])
        report = json.loads((self.output_dir / "metrics.json").read_text(encoding="utf-8"))
        self.assertIn("test", report)
        self.assertTrue(
            predictions["prediction"].eq(
                predictions["probability"].ge(report["threshold"]).astype(int)
            ).all()
        )

    def test_numeric_identifiers_keep_leading_zeroes_and_prediction_alignment(self):
        dataset = pd.read_csv(self.dataset_path)
        manifest = pd.read_csv(self.manifest_path)
        ids = dict(zip(dataset["CommentId"], [f"00{i}" for i in range(1, 10)]))
        videos = {"train-a": "001", "train-b": "002", "validation-a": "003", "test-a": "004"}
        for frame in (dataset, manifest):
            frame["CommentId"] = frame["CommentId"].map(ids)
            frame["VideoId"] = frame["VideoId"].replace(videos)
        dataset.to_csv(self.dataset_path, index=False)
        manifest.to_csv(self.manifest_path, index=False)

        run_training(self.dataset_path, self.manifest_path, self.output_dir)
        predictions = pd.read_csv(self.output_dir / "validation_predictions.csv", dtype={"CommentId": "string"})
        self.assertEqual(predictions["CommentId"].tolist(), ["005", "006"])

    def test_missing_video_is_rejected(self):
        dataset = pd.read_csv(self.dataset_path)
        dataset.loc[dataset["CommentId"].eq("x1"), "VideoId"] = None
        dataset.to_csv(self.dataset_path, index=False)

        with self.assertRaises(ValueError):
            run_training(self.dataset_path, self.manifest_path, self.output_dir)

    def test_blank_identifiers_are_rejected(self):
        original_dataset = pd.read_csv(self.dataset_path)
        original_manifest = pd.read_csv(self.manifest_path)
        for column in ("CommentId", "VideoId"):
            with self.subTest(column=column):
                dataset = original_dataset.copy()
                manifest = original_manifest.copy()
                original = dataset.loc[0, column]
                dataset.loc[dataset[column].eq(original), column] = "   "
                manifest.loc[manifest[column].eq(original), column] = "   "
                dataset.to_csv(self.dataset_path, index=False)
                manifest.to_csv(self.manifest_path, index=False)
                with self.assertRaisesRegex(ValueError, f"{column} must be present"):
                    run_training(self.dataset_path, self.manifest_path, self.output_dir)

    def test_rejects_text_leak_after_equivalent_whitespace_tokenization(self):
        dataset = pd.read_csv(self.dataset_path)
        dataset.loc[dataset["CommentId"].eq("v1"), "Text"] = "bad\t  insult"
        dataset.to_csv(self.dataset_path, index=False)
        with self.assertRaisesRegex(ValueError, "Identical text"):
            run_training(self.dataset_path, self.manifest_path, self.output_dir)

    def test_rejects_text_leak_after_vectorizer_lowercasing(self):
        dataset = pd.read_csv(self.dataset_path)
        dataset.loc[dataset["CommentId"].eq("v1"), "Text"] = "BAD INSULT"
        dataset.to_csv(self.dataset_path, index=False)

        with self.assertRaisesRegex(ValueError, "Identical text"):
            run_training(self.dataset_path, self.manifest_path, self.output_dir)

    def test_csv_text_keeps_numeric_and_literal_na_comments(self):
        dataset = pd.read_csv(self.dataset_path)
        dataset["Text"] = [str(value) for value in range(9)]
        dataset.to_csv(self.dataset_path, index=False)
        partitions = load_partitions(self.dataset_path, self.manifest_path)
        self.assertEqual(partitions["train"]["Text"].tolist(), ["0", "1", "2", "3"])

        dataset.loc[0, "Text"] = "NA"
        dataset.to_csv(self.dataset_path, index=False)
        partitions = load_partitions(self.dataset_path, self.manifest_path)
        self.assertEqual(partitions["train"].iloc[0]["Text"], "NA")

    def test_saved_model_reproduces_exported_probabilities_in_manifest_order(self):
        manifest = pd.read_csv(self.manifest_path).iloc[::-1]
        manifest.to_csv(self.manifest_path, index=False)
        report = run_training(self.dataset_path, self.manifest_path, self.output_dir)
        model = joblib.load(self.output_dir / "logistic_tfidf.joblib")
        predictions = pd.read_csv(self.output_dir / "validation_predictions.csv")
        self.assertEqual(predictions["CommentId"].tolist(), ["v2", "v1"])
        np.testing.assert_allclose(
            predictions["probability"],
            model.predict_proba(["kind person", "validationonly bad"])[:, 1],
        )
        repeated = run_training(self.dataset_path, self.manifest_path, self.root / "repeat")
        self.assertEqual(report, repeated)

    def test_evaluation_metrics_match_hand_calculated_probabilities(self):
        # Three positives in four training rows give p(toxic)=0.75 for every input.
        model = DummyClassifier(strategy="prior").fit(["a", "b", "c", "d"], [1, 1, 1, 0])
        partition = pd.DataFrame({"CommentId": ["a", "b"], "Text": ["first", "second"], "IsToxic": [0, 1]})
        predictions, metrics = evaluate(model, partition)
        self.assertEqual(predictions["probability"].tolist(), [0.75, 0.75])
        self.assertEqual(metrics["confusion_matrix"], [[0, 1], [0, 1]])
        self.assertEqual(metrics["precision"], 0.5)
        self.assertEqual(metrics["recall"], 1.0)
        self.assertAlmostEqual(metrics["f1"], 2 / 3)
        self.assertEqual(metrics["pr_auc"], 0.5)
        self.assertEqual(metrics["brier_score"], 0.3125)

    def test_validation_run_removes_stale_final_test_exports(self):
        run_training(self.dataset_path, self.manifest_path, self.output_dir, final_test=True)
        report = run_training(self.dataset_path, self.manifest_path, self.output_dir)
        self.assertNotIn("test", report)
        self.assertFalse((self.output_dir / "test_predictions.csv").exists())

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

import subprocess
import sys
from pathlib import Path

import pytest


@pytest.mark.parametrize(
    "script",
    [
        "train_transformer.py",
        "train_svm_tfidf.py",
        "compare_models.py",
        "run_ensemble.py",
    ],
)
def test_model_script_help_runs_from_repository_root(script):
    repository = Path(__file__).resolve().parents[2]

    result = subprocess.run(
        [sys.executable, str(repository / "scripts" / script), "--help"],
        cwd=repository,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    assert "usage:" in result.stdout


@pytest.mark.parametrize(
    "script",
    ["train_logistic_tfidf.py", "train_svm_tfidf.py", "train_transformer.py"],
)
def test_component_final_test_requires_frozen_ensemble_config(script):
    repository = Path(__file__).resolve().parents[2]

    result = subprocess.run(
        [sys.executable, str(repository / "scripts" / script), "--final-test"],
        cwd=repository,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode != 0
    assert "--ensemble-config" in result.stderr

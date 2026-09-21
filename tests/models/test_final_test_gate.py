import hashlib
import subprocess

import pytest

from src.moderation.models.final_test_gate import (
    validate_prediction_metadata,
    verify_committed_config,
    write_prediction_metadata,
)


def git(repository, *arguments):
    return subprocess.run(
        ["git", "-C", str(repository), *arguments],
        check=True,
        capture_output=True,
        text=True,
    )


def initialize_repository(tmp_path):
    git(tmp_path, "init")
    git(tmp_path, "config", "user.email", "tests@example.com")
    git(tmp_path, "config", "user.name", "Tests")
    marker = tmp_path / "README.md"
    marker.write_text("test repository\n", encoding="utf-8")
    git(tmp_path, "add", "README.md")
    git(tmp_path, "commit", "-m", "test: initialize")


def commit_config(tmp_path, manifest):
    config = tmp_path / "configs" / "ensemble.json"
    config.parent.mkdir()
    config.write_text(
        '{"schema_version":1,"weights":{"logistic":0.1,"svm":0.0,'
        '"transformer":0.9},"threshold":0.4,"source_sha256":{"manifest":"'
        + hashlib.sha256(manifest.read_bytes()).hexdigest()
        + '"}}\n',
        encoding="utf-8",
    )
    git(tmp_path, "add", "configs/ensemble.json")
    git(tmp_path, "commit", "-m", "feat: freeze ensemble")
    return config


def test_final_test_gate_accepts_only_config_equal_to_tracked_head_version(tmp_path):
    initialize_repository(tmp_path)
    manifest = tmp_path / "manifest.csv"
    manifest.write_text("CommentId,split\n1,test\n", encoding="utf-8")
    config = commit_config(tmp_path, manifest)

    digest = verify_committed_config(config, manifest)

    assert len(digest) == 64


@pytest.mark.parametrize("state", ["modified", "staged", "untracked"])
def test_final_test_gate_rejects_config_not_frozen_in_head(tmp_path, state):
    initialize_repository(tmp_path)
    manifest = tmp_path / "manifest.csv"
    manifest.write_text("CommentId,split\n1,test\n", encoding="utf-8")
    if state == "untracked":
        config = tmp_path / "configs" / "ensemble.json"
        config.parent.mkdir()
        config.write_text('{"schema_version": 1}\n', encoding="utf-8")
    else:
        config = commit_config(tmp_path, manifest)
        config.write_text('{"schema_version": 2}\n', encoding="utf-8")
        if state == "staged":
            git(tmp_path, "add", "configs/ensemble.json")

    with pytest.raises(ValueError, match="committed.*HEAD"):
        verify_committed_config(config, manifest)


def test_final_test_gate_rejects_config_from_a_different_repository(tmp_path):
    project = tmp_path / "project"
    foreign = tmp_path / "foreign"
    project.mkdir()
    foreign.mkdir()
    initialize_repository(project)
    initialize_repository(foreign)
    manifest = project / "manifest.csv"
    manifest.write_text("CommentId,split\n1,test\n", encoding="utf-8")
    config = commit_config(foreign, manifest)

    with pytest.raises(ValueError, match="committed.*HEAD"):
        verify_committed_config(config, manifest)


def test_prediction_metadata_proves_model_split_features_and_hashes(tmp_path):
    manifest = tmp_path / "split.csv"
    predictions = tmp_path / "predictions.csv"
    manifest.write_text("CommentId,split\n1,test\n", encoding="utf-8")
    predictions.write_text("CommentId,IsToxic,probability\n1,1,0.8\n", encoding="utf-8")

    write_prediction_metadata(
        predictions,
        model_name="transformer",
        split="test",
        manifest_path=manifest,
        config_sha256="a" * 64,
    )

    metadata = validate_prediction_metadata(
        predictions,
        expected_model="transformer",
        expected_split="test",
        manifest_path=manifest,
        expected_config_sha256="a" * 64,
    )
    assert metadata["feature_columns"] == ["Text"]

    predictions.write_text("CommentId,IsToxic,probability\n1,1,0.1\n", encoding="utf-8")
    with pytest.raises(ValueError, match="metadata"):
        validate_prediction_metadata(
            predictions,
            expected_model="transformer",
            expected_split="test",
            manifest_path=manifest,
            expected_config_sha256="a" * 64,
        )

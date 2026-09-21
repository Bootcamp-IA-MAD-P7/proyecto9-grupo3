import hashlib
import json
import subprocess
from pathlib import Path


def create_frozen_ensemble_config(repository: Path, manifest: Path) -> Path:
    subprocess.run(["git", "-C", str(repository), "init"], check=True, capture_output=True)
    subprocess.run(
        ["git", "-C", str(repository), "config", "user.email", "tests@example.com"],
        check=True,
    )
    subprocess.run(
        ["git", "-C", str(repository), "config", "user.name", "Tests"], check=True
    )
    config = repository / "configs" / "ensemble.json"
    config.parent.mkdir(parents=True, exist_ok=True)
    config.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "weights": {"logistic": 0.1, "svm": 0.0, "transformer": 0.9},
                "threshold": 0.4,
                "source_sha256": {
                    "manifest": hashlib.sha256(manifest.read_bytes()).hexdigest()
                },
            }
        ),
        encoding="utf-8",
    )
    subprocess.run(["git", "-C", str(repository), "add", "configs/ensemble.json"], check=True)
    subprocess.run(
        ["git", "-C", str(repository), "commit", "-m", "freeze test config"],
        check=True,
        capture_output=True,
    )
    return config

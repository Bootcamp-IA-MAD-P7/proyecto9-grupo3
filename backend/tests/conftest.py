"""Keep API tests independent of local credentials, files and shell settings."""

import os

import pytest


@pytest.fixture(autouse=True)
def isolated_settings(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("DATABASE_URL", raising=False)
    for key in tuple(os.environ):
        if key.startswith("MODERATION_"):
            monkeypatch.delenv(key)

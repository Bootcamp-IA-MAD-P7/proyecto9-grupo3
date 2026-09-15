"""Tests for pull-request rules in the dependency-light harness."""

from __future__ import annotations

import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from scripts import validate_harness


class ValidatePullRequestTests(unittest.TestCase):
    """Exercise GitHub pull-request payload validation without network access."""

    def pull_request_errors(
        self,
        title: str,
        *,
        base: str = "dev",
        head: str = "ci/SP-57-validate-conventional-commits",
        repository: str = validate_harness.CANONICAL_REPOSITORY,
        body: str | None = None,
    ) -> list[str]:
        body = body or (
            "- **Jira:** SP-57\n"
            "- **OpenSpec:** "
            "`openspec/changes/sp-57-validate-conventional-commits/`"
        )
        payload = {
            "pull_request": {
                "title": title,
                "body": body,
                "base": {"ref": base},
                "head": {"ref": head, "repo": {"full_name": repository}},
            }
        }
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".json", delete=False, encoding="utf-8"
        ) as event:
            json.dump(payload, event)
            event_path = event.name
        try:
            with patch.dict(
                os.environ,
                {"GITHUB_EVENT_NAME": "pull_request", "GITHUB_EVENT_PATH": event_path},
                clear=False,
            ):
                return validate_harness.validate_pull_request()
        finally:
            Path(event_path).unlink()

    def test_accepts_allowed_title_types(self) -> None:
        for title in (
            "feat: add toxicity prediction endpoint",
            "fix: reject empty comment input",
            "docs: document Git and Jira workflow",
            "test: cover text preprocessing",
            "ci: add repository quality workflow",
            "chore: configure project tooling",
        ):
            with self.subTest(title=title):
                self.assertEqual([], self.pull_request_errors(title))

    def test_accepts_a_lowercase_scope(self) -> None:
        self.assertEqual(
            [], self.pull_request_errors("feat(api): add toxicity prediction endpoint")
        )

    def test_rejects_an_unapproved_type(self) -> None:
        errors = self.pull_request_errors("refactor: simplify validator")
        self.assertTrue(any("Conventional Commits" in error for error in errors))

    def test_rejects_a_title_without_a_colon(self) -> None:
        errors = self.pull_request_errors("feat add toxicity prediction endpoint")
        self.assertTrue(any("Conventional Commits" in error for error in errors))

    def test_rejects_an_uppercase_description(self) -> None:
        errors = self.pull_request_errors("feat: Add toxicity prediction endpoint")
        self.assertTrue(any("Conventional Commits" in error for error in errors))

    def test_accepts_a_release_pr_title(self) -> None:
        self.assertEqual(
            [],
            self.pull_request_errors(
                "chore(release): prepare v0.1.0", base="main", head="dev"
            ),
        )

    def test_accepts_a_non_material_openspec_reason(self) -> None:
        self.assertEqual(
            [],
            self.pull_request_errors(
                "docs: clarify contribution guide",
                body=(
                    "- **Jira:** SP-13\n"
                    "- **OpenSpec:** N/A — documentation-only clarification"
                ),
            ),
        )

    def test_rejects_a_missing_openspec_field(self) -> None:
        errors = self.pull_request_errors(
            "docs: clarify contribution guide", body="- **Jira:** SP-13"
        )
        self.assertIn("PR body must include an OpenSpec field.", errors)

    def test_rejects_an_unjustified_non_material_openspec(self) -> None:
        errors = self.pull_request_errors(
            "docs: clarify contribution guide",
            body="- **Jira:** SP-13\n- **OpenSpec:** N/A",
        )
        self.assertIn(
            "OpenSpec must use openspec/changes/<change-name>/ or N/A — <non-material reason>.",
            errors,
        )

    def test_rejects_an_incomplete_openspec_path(self) -> None:
        errors = self.pull_request_errors(
            "docs: clarify contribution guide",
            body="- **Jira:** SP-13\n- **OpenSpec:** openspec/changes/",
        )
        self.assertIn(
            "OpenSpec must use openspec/changes/<change-name>/ or N/A — <non-material reason>.",
            errors,
        )

    def test_rejects_arbitrary_text_containing_an_openspec_path(self) -> None:
        errors = self.pull_request_errors(
            "docs: clarify contribution guide",
            body=(
                "- **Jira:** SP-13\n"
                "- **OpenSpec:** arbitrary text openspec/changes/sp-57-validate-conventional-commits/"
            ),
        )
        self.assertIn(
            "OpenSpec must use openspec/changes/<change-name>/ or N/A — <non-material reason>.",
            errors,
        )

    def test_rejects_a_nonexistent_openspec_path(self) -> None:
        errors = self.pull_request_errors(
            "docs: clarify contribution guide",
            body=(
                "- **Jira:** SP-13\n"
                "- **OpenSpec:** `openspec/changes/nonexistent-change/`"
            ),
        )
        self.assertIn("OpenSpec path must exist in this repository.", errors)

    def test_rejects_a_missing_jira_field(self) -> None:
        errors = self.pull_request_errors(
            "docs: clarify contribution guide",
            body="- **OpenSpec:** N/A — documentation-only clarification",
        )
        self.assertIn("PR body must include a Jira field with an SP-<number> key.", errors)


class SensitivePathTests(unittest.TestCase):
    def test_rejects_env_file(self) -> None:
        self.assertTrue(validate_harness.is_sensitive_path(".env"))

    def test_rejects_local_env_file(self) -> None:
        self.assertTrue(validate_harness.is_sensitive_path("config/.env.local"))

    def test_allows_env_example(self) -> None:
        self.assertFalse(validate_harness.is_sensitive_path(".env.example"))

    def test_rejects_key_or_credentials(self) -> None:
        self.assertTrue(validate_harness.is_sensitive_path("certs/private.key"))
        self.assertTrue(validate_harness.is_sensitive_path("credentials.json"))

    def test_rejects_reserved_local_data_path(self) -> None:
        self.assertTrue(validate_harness.is_sensitive_path("data/raw/comments.csv"))

    def test_allows_normal_repository_file(self) -> None:
        self.assertFalse(validate_harness.is_sensitive_path("docs/README.md"))

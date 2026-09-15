"""Validate repository harness invariants without third-party dependencies."""

from __future__ import annotations

import json
import os
import re
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
REQUIRED_PATHS = (
    "AGENTS.md",
    "docs/base-standards.md",
    "docs/HARNESS.md",
    "openspec/config.yaml",
    ".agents/skills/enrich-jira-story/SKILL.md",
    ".agents/skills/adversarial-review/SKILL.md",
    ".github/pull_request_template.md",
)
BRANCH_PATTERN = re.compile(
    r"^(feature|fix|docs|test|ci|chore)/SP-\d+-[a-z0-9][a-z0-9-]*$"
)
INTEGRATION_BRANCHES = {"dev", "main"}
JIRA_PATTERN = re.compile(r"\bSP-\d+\b", re.IGNORECASE)
CANONICAL_REPOSITORY = "Bootcamp-IA-MAD-P7/proyecto9-grupo3"
CONVENTIONAL_COMMIT_TITLE_PATTERN = re.compile(
    r"^(feat|fix|docs|test|ci|chore)(\([a-z0-9][a-z0-9-]*\))?!?: [a-z0-9].+$"
)
JIRA_FIELD_PATTERN = re.compile(
    r"(?mi)^-\s+(?:\*\*)?Jira:\s*(?:\*\*)?\s*SP-\d+\s*$"
)
OPENSPEC_FIELD_PATTERN = re.compile(
    r"(?mi)^-\s+(?:\*\*)?OpenSpec:\s*(?:\*\*)?\s*(.+?)\s*$"
)
NON_MATERIAL_OPENSPEC_PATTERN = re.compile(r"^N/A\s*[—-]\s*\S.*$", re.IGNORECASE)
OPENSPEC_CHANGE_PATH_PATTERN = re.compile(
    r"^`?(openspec/changes/[a-z0-9][a-z0-9-]*/?)`?$"
)
SENSITIVE_FILENAMES = {"credentials.json", "service-account.json", "secrets.json"}
SENSITIVE_DATA_DIRECTORIES = {"data/local", "data/raw", "data/private", "datasets"}


def is_sensitive_path(relative_path: str) -> bool:
    """Return whether a tracked path is reserved for secrets or real data."""
    normalized = relative_path.replace("\\", "/")
    while normalized.startswith("./"):
        normalized = normalized[2:]
    normalized = normalized.lstrip("/")
    path = Path(normalized)
    name = path.name
    if name == ".env" or (name.startswith(".env.") and name != ".env.example"):
        return True
    if name in SENSITIVE_FILENAMES or name.startswith("service-account-"):
        return True
    if path.suffix.lower() in {".pem", ".key"}:
        return True
    parts = path.parts
    return any(
        "/".join(parts[index : index + 2]) in SENSITIVE_DATA_DIRECTORIES
        for index in range(len(parts) - 1)
    )


def read(relative_path: str) -> str:
    return (ROOT / relative_path).read_text(encoding="utf-8")


def current_branch() -> str | None:
    result = subprocess.run(
        ["git", "branch", "--show-current"],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    return result.stdout.strip() or None


def tracked_files() -> list[str]:
    result = subprocess.run(
        ["git", "ls-files"],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    return result.stdout.splitlines()


def validate_skill(path: Path) -> list[str]:
    errors: list[str] = []
    text = path.read_text(encoding="utf-8")
    if not text.startswith("---\n"):
        return [f"{path.relative_to(ROOT)}: missing YAML frontmatter"]
    frontmatter = text.split("---", 2)[1]
    if not re.search(r"(?m)^name: [a-z0-9-]+$", frontmatter):
        errors.append(f"{path.relative_to(ROOT)}: invalid or missing name")
    if not re.search(r"(?m)^description: .+", frontmatter):
        errors.append(f"{path.relative_to(ROOT)}: missing description")
    return errors


def validate_pull_request() -> list[str]:
    if os.getenv("GITHUB_EVENT_NAME") != "pull_request":
        return []
    event_path = os.getenv("GITHUB_EVENT_PATH")
    if not event_path or not Path(event_path).exists():
        return ["Pull request event payload is unavailable."]
    payload = json.loads(Path(event_path).read_text(encoding="utf-8"))
    pull_request = payload.get("pull_request", {})
    title = pull_request.get("title") or ""
    body = pull_request.get("body") or ""
    head_details = pull_request.get("head", {})
    head = head_details.get("ref") or ""
    head_repository = head_details.get("repo") or {}
    head_repository_name = head_repository.get("full_name") or ""
    base = pull_request.get("base", {}).get("ref") or ""
    errors: list[str] = []
    if not CONVENTIONAL_COMMIT_TITLE_PATTERN.fullmatch(title):
        errors.append(
            "PR title must use Conventional Commits: "
            "<feat|fix|docs|test|ci|chore>(scope)?: lowercase description."
        )
    if base == "main":
        if head != "dev":
            errors.append("Pull requests into main must promote the dev branch.")
        if head_repository_name.casefold() != CANONICAL_REPOSITORY.casefold():
            errors.append(
                "Pull requests into main must promote dev from "
                f"{CANONICAL_REPOSITORY}."
            )
    if base != "main" and not BRANCH_PATTERN.fullmatch(head):
        errors.append(
            "PR branch must match <type>/SP-<number>-<short-description>."
        )
    if not JIRA_PATTERN.search(f"{title}\n{body}\n{head}"):
        errors.append("PR title, body, or branch must reference an SP Jira key.")
    if not JIRA_FIELD_PATTERN.search(body):
        errors.append("PR body must include a Jira field with an SP-<number> key.")
    openspec_field = OPENSPEC_FIELD_PATTERN.search(body)
    if not openspec_field:
        errors.append("PR body must include an OpenSpec field.")
    else:
        openspec_value = openspec_field.group(1).strip("` ")
        openspec_path = OPENSPEC_CHANGE_PATH_PATTERN.fullmatch(openspec_value)
        if openspec_path:
            if not (ROOT / openspec_path.group(1)).is_dir():
                errors.append("OpenSpec path must exist in this repository.")
        elif not NON_MATERIAL_OPENSPEC_PATTERN.fullmatch(openspec_value):
            errors.append(
                "OpenSpec must use openspec/changes/<change-name>/ or "
                "N/A — <non-material reason>."
            )
    return errors


def validate() -> list[str]:
    errors: list[str] = []
    for relative_path in REQUIRED_PATHS:
        if not (ROOT / relative_path).is_file():
            errors.append(f"Missing required harness file: {relative_path}")

    if errors:
        return errors

    if "docs/base-standards.md" not in read("AGENTS.md"):
        errors.append("AGENTS.md must point to docs/base-standards.md.")

    config = read("openspec/config.yaml")
    if "schema: spec-driven" not in config:
        errors.append("OpenSpec must use the spec-driven schema.")
    if "docs/base-standards.md" not in config:
        errors.append("OpenSpec context must reference the canonical standards.")

    for skill in (ROOT / ".agents" / "skills").glob("*/SKILL.md"):
        errors.extend(validate_skill(skill))

    changes_root = ROOT / "openspec" / "changes"
    if changes_root.exists():
        for change in changes_root.iterdir():
            if not change.is_dir() or change.name == "archive":
                continue
            for required in ("proposal.md", "design.md", "tasks.md"):
                if not (change / required).is_file():
                    errors.append(f"{change.name}: missing {required}")
            if not any((change / "specs").glob("*/spec.md")):
                errors.append(f"{change.name}: missing specs/<capability>/spec.md")

    branch = current_branch()
    if (
        branch
        and branch not in INTEGRATION_BRANCHES
        and not BRANCH_PATTERN.fullmatch(branch)
    ):
        errors.append(
            f"Branch {branch!r} must match <type>/SP-<number>-<description>."
        )

    for tracked in tracked_files():
        if is_sensitive_path(tracked):
            errors.append(f"Sensitive or real-data path is tracked: {tracked}")

    errors.extend(validate_pull_request())
    return errors


if __name__ == "__main__":
    failures = validate()
    if failures:
        print("Harness validation failed:")
        for failure in failures:
            print(f"- {failure}")
        sys.exit(1)
    print("Harness validation passed.")

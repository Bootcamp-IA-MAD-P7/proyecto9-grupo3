## Why

SP-66 turns the approved repository-security policy into a small, dependency-free
guard. It prevents clearly sensitive filenames and reserved local-data paths
from being tracked while keeping the control proportional to the project's
short delivery window.

## What Changes

- Extend `.gitignore` for environment files, obvious key/credential files, and
  local real-data directories.
- Document the rule in `docs/base-standards.md`.
- Extend the existing harness with filename/path validation and standard-library
  tests.

## Non-goals

- Secret scanning, content inspection, GitHub Secret Scanning, AWS Secrets
  Manager, deployment-secret management, or new dependencies and workflows.

## Context

The repository must not contain credentials, environment files, personal data,
or real dataset material. A filename/path check is sufficient for this initial
policy and avoids introducing a toolchain before the application stack exists.

## Decision

Use `.gitignore` as the contributor-facing prevention and extend
`scripts/validate_harness.py` with a pure-Python `is_sensitive_path` check over
tracked files. Reject `.env` variants except `.env.example`, obvious key and
credential filenames, and the reserved `data/local`, `data/raw`,
`data/private`, and `datasets` paths. Do not inspect file contents.

## Verification and rollback

Unit tests exercise accepted and rejected paths. The harness and diff checks
provide repository evidence. Reverting this focused commit removes the rule;
no external configuration is changed.

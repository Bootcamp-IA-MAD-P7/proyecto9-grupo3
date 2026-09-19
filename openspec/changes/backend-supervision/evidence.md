# Evidence for backend-supervision

Local verification on 2026-09-18 in the detached Codex worktree. The user
explicitly waived the Jira prerequisite for this learning work. Existing
uncommitted authentication and review files were preserved. This work is not
represented as merged, deployed or reviewed by another teammate.

## Checks

- `python -m pytest backend/tests/test_supervision.py -q`: 11 passed. Covers
  migration from versions 2 and 3, permissions, resolution, active and escalated
  reassignment, reopening, information exchange, second review, status errors
  and concurrent approve/reject. Expired supervised claims restore their
  controlled state.
- `python -m pytest -q`: 91 passed and 6 unittest subtests passed. Two upstream
  deprecation warnings remain in FastAPI/Starlette's TestClient dependencies.
- `python -m pip check`: no broken requirements.
- `openspec validate backend-supervision --strict`: valid.
- `python scripts/validate_harness.py`: passed in this detached worktree.
  This does not establish Jira traceability for a future PR; the user waived
  that requirement for this local work only.
- `git diff --check`: no whitespace errors. Git printed line-ending conversion
  notices for existing tracked files. An additional whitespace scan of all
  newly created supervision files passed.
- A temporary Uvicorn process served real HTTP on loopback against a temporary
  SQLite database. Login, escalation, resolution, reopening, approval,
  reassignment, second review and ordered history all passed. The temporary
  process and database were removed afterward.

## Contract and privacy observations

- A moderator receives 403 on supervisor routes; missing sessions receive 401.
- A pending reopening never returns to the general PENDING queue. Approval
  leaves it REOPENED until a supervisor assigns a new reviewer.
- An expired supervised claim restores ESCALATED or REOPENED, keeping the case
  outside the general queue.
- The earlier review remains in `reviews`; a second review adds a new row.
- Simultaneous approval and rejection produce one success and one 409, with
  one terminal audit event.
- Audit rows do not contain the stored synthetic comment text. Human-authored
  reasons and clarification notes are stored in domain tables and returned
  only to authenticated staff with `Cache-Control: no-store`.
- A local removal recommendation produces no external YouTube action.

## Limits

The worktree has prior uncommitted steps 3 and 5, and no commit, push, PR,
teammate review, merge or deployment was performed here. Existing local SQLite
files should be backed up before a version 4 startup; migration is forward-only.
The model and demo scores remain simulated, and frontend integration remains
for step 7.

# Evidence for backend-review-history

Local verification on 2026-09-18 in the detached worktree. The user explicitly
waived the Jira prerequisite for this learning increment. No Jira item, team
approval, PR, merge or deployment is claimed.

## Automated and runtime checks

- `python -m pytest backend/tests/test_review.py -q`: 17 passed. Covers schema
  migration, ordered text-free queue, two competing API instances, lease expiry,
  access control, four decisions, history and idempotent synthetic seed.
- `python -m pytest backend/tests -q`: 61 passed; two deprecation warnings from
  installed Starlette/FastAPI dependencies. No test failures.
- `python -m pip check`: no broken requirements.
- `python scripts/validate_harness.py`: passed.
- `openspec validate backend-review-history --strict`: valid.
- `git diff --check`: passed. Git reported only LF/CRLF conversion notices for
  existing tracked files.
- A temporary local Uvicorn server against an isolated SQLite file passed real
  HTTP requests for login, queue, claim, competing claim (409), nonowner
  content access (403), owner reveal, review creation (201), ordered history
  and `Cache-Control: no-store`. Repeating the synthetic seed inserted zero
  duplicates. The temporary server and database were removed.

## Independent review and repair

An independent code review found that the initial implementation read the
clock before `BEGIN IMMEDIATE`. A request waiting on another SQLite writer
could therefore use an old time to reveal content or save a decision after
its lease had expired. Three regression cases first reproduced the defect for
claim, reveal and review. The repository now reads the clock after acquiring
the write lock; all three and the full suite pass.

## Limits

Demo scores and texts are synthetic; no actual ingestion or model inference
is present. `ESCALATED` marks work for later human handling, not a completed
supervisor decision. The local SQLite migration is forward-only; back up a
valuable version 1 database before starting the new application.

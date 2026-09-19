# Proposal

## Why

The backend already records human decisions and escalations, but supervisors
cannot resolve or reassign cases and moderators cannot request a controlled
reopening. The next learning increment completes these human workflows.

## What Changes

- Add persistent supervisor dispositions, reassignment and reopening requests.
- Add supervisor-only routes and moderator request/follow-up routes.
- Preserve previous reviews and extend the text-free audit history.
- Migrate existing SQLite version 2 or 3 databases to version 4.

## Capabilities

### New Capabilities

- `backend-supervision`: Supervisor resolution, reassignment, and controlled reopening.

### Modified Capabilities

None. The prior review contract remains; this adds later lifecycle actions.

## Impact

SQLite schema, comment history, FastAPI routes, OpenAPI, tests and the learning
guide. Existing uncommitted authentication and review work is preserved.
The user has explicitly waived the repository's Jira requirement for this work.

## Non-goals

No YouTube action, user sanctions, real dataset ingestion or automatic model
decisions. Recommendation to remove a comment is only recorded locally.

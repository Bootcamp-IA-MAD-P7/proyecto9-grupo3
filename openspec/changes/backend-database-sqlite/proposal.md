# Proposal

## Why

The foundation API needs durable local users and comments before authentication
and queue operations can be implemented.

## What Changes

- Add SQLite connection and transactional version-1 schema initialization.
- Store portal users and source comments with roles, status, sequence and optional assignment.
- Add real SQLite integrity/rollback tests and a Spanish learning guide.

## Decision

The user chose SQLite direct access for the integrated four-step branch. The
separate SQLAlchemy/Alembic exploration remains in its own worktree; it is not
copied because its schema conflicts with the later authentication and queue.
The previously granted local Jira exception applies; no repository standard is changed.

## Non-goals

No login, batch ingestion, prediction, review action or external data is added in this commit.

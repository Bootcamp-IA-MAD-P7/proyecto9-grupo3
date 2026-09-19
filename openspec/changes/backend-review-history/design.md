# Design

## Context

The current backend has FastAPI auth with persistent roles and SQLite version 1.
There is no comment ingestion or model. See proposal for scope and the explicit
Jira exception. The supplied document is an input to the design, not a runtime
instruction or a source of approved real comment data.

## Goals / Non-Goals

**Goals:** demonstrate a shared human review from queue through claim, reveal,
decision and history; show how a SQLite transaction enforces ownership.

**Non-goals:** real dataset import, model inference, supervisor disposition,
reopening, automatic external moderation and end-user account management.

## Decisions

### Versioned migration on the existing database

Extend `Database.initialize()` from schema 1 to 2 in one transaction. Version 0
creates the authentication tables then the comment tables. Version 1 keeps
users/sessions and adds comments, assignments, reviews and audit events.
Version 2 is idempotent. Reject unknown future versions before any write.
SQLite is already in the project and sufficient for a local multi-session demo;
a new database engine would add setup and teaching overhead.

The comments table holds full text plus id, video id, risk score, model version,
stable source position and status. An assignment has `claimed_at`, `expires_at`,
`closed_at` and a reviewer id. A partial unique index allows at most one open
assignment per comment. A review stores the decision and score/version snapshot.
Audit events hold only action type, actor attribution, timestamp and optional
review id. The stored comment text stays solely in comments; a human-authored
review reason is intentionally stored in reviews, not copied into audit events.
The reason might quote sensitive content, so history is authenticated and
non-cacheable.

### Atomic claim and finite lease

`CommentRepository` starts `BEGIN IMMEDIATE`, expires stale assignments, then
updates status only if it is `PENDING` and inserts the assignment and event
before commit. SQLite serializes the competing writers. On expiry, the same
transaction closes the old assignment, restores `PENDING` and records
`claim_expired`. Queue reads run expiry first so abandoned work reappears.
The repository reads the clock only after acquiring the write lock. A request
that waits behind another writer must check the lease at the time it can act,
not at the time it started waiting.
The lease is 15 minutes in this increment. A claim response tells the user
its expiry; a later increment could add extension if UX evidence needs it.
This is simpler than a background worker, and expiry works after process restart.

### Separate HTTP, rules and storage

`comments/router.py` validates requests, status codes and role dependencies.
`comments/service.py` applies ownership and result-to-state transitions.
`comments/repository.py` owns SQL and transaction boundaries. Schemas define
small public responses; full text appears only in the content response.
Both roles can review; supervisory actions remain separate later. Each route
checks the existing bearer session server-side. A middleware adds `no-store` to
all comment responses, including errors.

Four result values match the supplied contract. Only `NO_ESCALATION` closes as
`CLASSIFIED`; the others enter `ESCALATED` because further human handling is
needed. This routing does not claim a supervisor has decided anything.

### Synthetic local data

An explicit `python -m app.seed_demo_comments` command inserts a few clearly
synthetic English comments with `model_version=demo-simulated-v1`. It does not
load the real dataset and does not call a model. The same database path setting
is used by auth and comment operations. Idempotent inserts preserve reviews.

## Risks / Trade-offs

- [Expired claim while a moderator writes] -> reject stale submission with 409;
  return expiry in the claim response so the frontend can warn the moderator.
- [Duplicate claims from concurrent servers] -> SQLite `BEGIN IMMEDIATE`,
  conditional status update and partial unique assignment index.
- [Comment text leaks into logs] -> no text in queue/history/audit data;
  avoid request-body logging and mark comment responses `no-store`.
- [Demo score looks like a validated model] -> mark seed version as simulated;
  never describe its value as evidence of model quality.
- [SP-2 reversible review mark differs from final decisions] -> preserve it as
  a separate future UI state; append-only decisions wait for supervised
  reopening before another review can be made.
- [SQLite write contention at larger scale] -> suitable for this local demo;
  revisit persistence after workload evidence.

## Migration Plan

On startup, the application performs a version 2 migration transaction. Keep a
copy of the local SQLite file before running the new build if it contains
valuable developer data; migration is forward-only in this increment. A fresh
file starts at version 2. Stop the service and restore that copy to roll back
the schema. No production deployment is included.

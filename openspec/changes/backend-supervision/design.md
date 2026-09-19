# Design

## Context

The current local worktree has SQLite schema version 2, token authentication,
role checks, exclusive claims and append-only reviews. The user authorized
building step 6 without Jira. The supplied `back1.txt` is product input, not
an instruction source. Its pending request rule is more detailed than SP-2's
separate reversible visual reviewed mark.

## Goals / Non-Goals

**Goals:** close escalations, move work between staff and allow supervisor-led
reopening without erasing earlier decisions.

**Non-goals:** external moderation, account administration or changing the
visual reviewed mark. No raw comment text enters audit data.

## Decisions

### SQLite version 4

Add `reopen_requests`, `reopen_updates` and `supervisor_actions`. Rebuild
`audit_events` with the existing rows plus nullable references to requests
and actions and a constrained set of new event types. Use one migration
transaction and advance `user_version` only after all changes succeed.
Add `assignments.return_status` to restore the correct state after expiry.
Existing ordinary claims default to PENDING; supervised claims retain
ESCALATED or REOPENED. Existing version 3 databases gain this column.
SQLite remains appropriate for the small shared demo; a separate event store
would add infrastructure without value here.

### Transactional lifecycle

Each operation begins `BEGIN IMMEDIATE`, reads the current state and actor,
then changes the comment, assignment, request and audit together. A partial
unique index permits only one outstanding reopening request per comment.
Conflict returns 409, unknown ids 404 and unauthorized roles 403. A missing
or expired bearer session returns 401 through the existing dependency.

Reopening is requested only from CLASSIFIED or RESOLVED. Pending requests use
REOPEN_REQUESTED, with the previous state stored in the request. Rejection
restores it. Approval sets REOPENED, and a supervisor must reassign before a
new review. This keeps the case out of the ordinary queue while unattended. Expired
supervised claims also return to ESCALATED or REOPENED.

An information request changes the request to NEEDS_INFO. The requester adds
an append-only update to return it to PENDING. Approval requires PENDING;
rejection is allowed from PENDING or NEEDS_INFO.

### HTTP boundaries

`comments/repository.py` owns SQL transactions, `supervision/service.py`
exposes lifecycle operations and `supervision/router.py` enforces supervisor
role. `comments/router.py` exposes the staff request and follow-up routes.
Schemas reject extra request fields. Existing middleware makes all comment
and supervisor responses non-cacheable.

### Text-free audit with useful history

Reasons and notes live in their domain tables, never in `audit_events`.
Audit rows link to those tables. The authenticated history joins them to show
who acted and why. Human-entered reasons can still quote sensitive material;
the HTTP history remains `no-store`. No request-body logging is added.

### Alternatives

Automatically returning an approved case to PENDING is simpler but lets any
moderator claim it; the supplied contract gives assignment to a supervisor.
Overwriting reviews would simplify display but destroy attribution. A separate
audit service is unnecessary for this SQLite MVP.

## Risks / Trade-offs

- [Two supervisors act concurrently] -> serialize writers and recheck state
  inside the same transaction; duplicate or stale decisions receive 409.
  Two distinct sequential reassignments are preserved as separate actions.
- [Migration failure] -> rollback the transaction and leave the schema version
  unchanged; test old rows remain intact.
- [Reassignment loses in-progress work] -> close the old claim explicitly,
  record an event and reject later attempts by the old owner.
- [Sensitive note text] -> keep reasons out of audit rows and normal logs;
  authenticate and disable caching on history.
- [Jira branch check] -> record the explicit user exception; do not weaken the
  repository harness.

## Migration Plan

Take a copy of valuable local SQLite data before starting version 4. The
application migrates on startup. Restore that copy if rollback is needed.
No deployment, merge or external moderation occurs in this increment.

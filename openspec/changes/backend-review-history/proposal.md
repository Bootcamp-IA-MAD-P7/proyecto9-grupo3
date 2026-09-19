# Proposal

## Why

The backend authenticates staff but has no shared comment state. Moderators
cannot reserve an item, inspect its text safely, record a decision or see who
made previous decisions. This increment makes that human review path executable.

## What Changes

- Add a versioned SQLite migration for comments, assignments, reviews and audit events.
- Expose an authenticated queue without comment text, atomic claim with a finite
  lease, content reveal for the active assignee and append-only human decisions.
- Expose authenticated history with reviewer attribution and no comment text.
- Provide explicit synthetic demo comments, behavioral tests and a learning guide.

## Capabilities

### New Capabilities

- `comment-review-history`: Shared claim, controlled reveal, human review and
  inspectable comment history.

### Modified Capabilities

None. The existing reversible review *mark* in the SP-2 product definition is
distinct from an append-only final review decision. No undo route is changed.

## Impact

Changes `backend/app/database.py` and `backend/app/main.py`; adds a comments
module, a synthetic seed command, tests and `docs/backend/05-revision-e-historico.md`.
Uses the existing authentication roles and SQLite database. No external service.

## Facts, assumptions and non-goals

- The current worktree has authentication and SQLite schema version 1, but no
  comment tables or comment APIs. Its uncommitted authentication changes are
  preserved as prerequisites of this local implementation.
- The user explicitly selected step 5 and previously waived a Jira identifier
  for this local learning work. That waiver does not change repository policy.
- A claim expires after 15 minutes unless a decision is submitted. This avoids
  abandoned items remaining inaccessible; it is a review workflow assumption.
- `NO_ESCALATION` closes as `CLASSIFIED`. The three results requiring further
  handling (`ESCALATE_TO_SUPERVISOR`, `INSUFFICIENT_CONTEXT`,
  `TRANSFER_REQUESTED`) enter `ESCALATED` for the next supervisory increment.
- Supervisor disposition, reassignment, reopening, model integration, dataset
  import and YouTube actions remain outside this increment.

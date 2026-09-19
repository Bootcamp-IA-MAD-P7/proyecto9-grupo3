# Proposal

## Why

The backend increments are isolated: the older import queue uses a different
SQLite schema from review and supervision, and no browser interface exercises
the complete human workflow. A model artifact may be produced separately but
the API has no adapter to load it.

## What Changes

- Merge import, review and supervision into SQLite schema version 5, migrating
  the known legacy schema shapes while preserving data.
- Add supervisor import and a paginated, text-free queue alongside the existing
  review routes.
- Add an optional trusted local sklearn model adapter and explicit simulated mode.
- Serve a minimal same-origin browser interface for human review and supervision.
- Add integration tests and a Spanish walkthrough.

## Capabilities

### New Capabilities

- `backend-integration`: One local browser-to-API human moderation path.

### Modified Capabilities

- `comment-review-history`: Imported comments enter the existing review path.

## Impact

Touches database, comments, application assembly, configuration, dependencies,
tests and docs. Adds `frontend/`. No YouTube action or deployment.

## Scope decision

The user explicitly approved this local learning increment and waived Jira for
it. The raw dataset and trained artifact are absent, so model quality remains
unverified. The UI only displays the result of human and model actions; it
never moderates YouTube automatically.

# Backend integration design

## Goal

Connect the existing local moderation API to a small same-origin frontend and a
configurable TF-IDF/logistic-regression inference artifact. Preserve the human
workflow, authorization and audit behavior while reconciling the independently
developed queue and supervision data models.

## Existing context

The current worktree contains uncommitted authentication and review code on top
of the original foundation. `dev` contains ingestion, paginated queue and a
simulated scorer. A separate worktree contains completed supervision code and
tests. The model branch contains training code but no trained artifact or raw
dataset is available in the inspected project folders. The user authorized
working without a Jira key and asked for a minimal frontend in this project.

## Architecture

One FastAPI process serves `/ui/` and the existing JSON API. The browser calls
relative URLs, so no cross-origin configuration is needed. The UI owns display
state; the API owns sessions, roles, claims, review transitions and history.
Bearer tokens remain in JavaScript memory and vanish on refresh. The UI sets
comment text with `textContent` only after an explicit reveal request. Responses
for authenticated endpoints carry `Cache-Control: no-store`.

The backend selects either a deterministic `SIMULATED` scorer or a `MODEL`
adapter. Selecting `MODEL` requires a local trusted joblib pipeline path and its
metadata; missing or invalid files fail startup or import explicitly. The
adapter calls `predict_proba` for `IsToxic`, validates its output and returns
score, uncertainty, model version and source. It never assigns moderation
status. A synthetic trained fixture proves the adapter and API contract; it is
not evaluation evidence for the project's dataset. No source dataset or model
artifact is committed.

## Data reconciliation

Use the reviewed comment, assignment, review, audit and supervision tables as
the target schema. Add `uncertainty` and `score_source` to comments and import
into this schema. The queue uses `source_order` as its stable tie breaker and a
paginated response matching the accepted `dev` contract.

SQLite `user_version=3` is ambiguous between the `dev` queue schema and the
supervision worktree. Migration must inspect table columns before changing
anything. Recognize both variants, preserve users, sessions, comments and
existing decisions, and reject an unknown shape without writes. The target
version is 5. Existing version 4 gets the scoring columns only. Migrations run
in one `BEGIN IMMEDIATE` transaction. Tests cover fresh databases and each
known old shape. No local `.db` file was found in the two inspected folders;
document backup of any valuable database before first startup.

## User journey

The user logs in, sees a text-free prioritized queue, reserves a comment,
reveals its content intentionally, submits a human decision and sees its
history. A supervisor can import synthetic comments, inspect escalations,
resolve and reassign, and decide reopen requests. The interface shows loading,
empty, validation, authentication, permission, conflict, scoring-unavailable and
network states. A 409 refreshes the queue instead of pretending a claim worked.

## Testing and limits

Use real SQLite files in isolated tests, the API client for contract and
authorization checks, and a browser or HTTP smoke run for the same-origin UI.
Model tests train only synthetic text. Check raw text absence from queue,
history, audit rows and logs. No YouTube action, deployment, merge or real model
quality claim is part of this change. A real dataset and trained artifact are
required before claiming evaluated model performance.

## Alternatives

React/Vite would add a separate build and server, making the first integrated
request path harder to teach. Serving a small static UI is sufficient for this
internal demo. Replacing the reviewed supervision schema with the `dev` table
layout would require more edits to transactional code and increases risk to
claims and reopenings. The chosen migration explicitly preserves both known
data shapes.

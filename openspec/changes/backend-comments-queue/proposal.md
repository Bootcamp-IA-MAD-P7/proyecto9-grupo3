# Proposal

## Why

The API can authenticate reviewers but has no comments to review. This local learning
increment connects validated comment input to a persistent, prioritized queue.

## What Changes

- Add supervisor-only JSON batch ingestion and a text-free, paginated queue for both roles.
- Introduce a scoring interface with an explicitly simulated, deterministic adapter.
- Migrate SQLite schema version 2 to version 3 without deleting users, sessions or comments; score existing comments with the simulation.
- Document the boundaries and exercises in Spanish.

## Facts, assumptions and authorization

- The user explicitly asked to proceed step by step and waive the Jira requirement for this work.
- `back1.txt` provides reference fields `CommentId`, `VideoId`, `Text`; its suggestions do not override the user request or repository product safety rules.
- No licensed real dataset is stored in the repository. Tests use synthetic comments.
- Page numbers and a supervisor-only import route are local MVP choices; the subsequent frontend may refine these contracts.

## Non-goals

No actual classifier, model quality claim, CSV data license decision, text reveal,
claim/review action, YouTube connection, or automatic moderation action.

# Tasks

## 1. Persistence and lifecycle

- [x] 1.1 Add failing migration tests for a fresh database and version 1 data preservation, then migrate `Database.initialize()` to version 2 with constrained comment, assignment, review and audit tables; verify the focused tests pass.
- [x] 1.2 Add failing tests for pending summaries, stable ranking, missing/empty queues, atomic competing claims and lease expiry; implement repository transactions and verify those tests pass.

## 2. Protected review workflow

- [x] 2.1 Add failing tests for owner-only text reveal, 401/403/404 responses, no-store caching and text-free audit rows; implement the protected content route and verify those tests pass.
- [x] 2.2 Add failing tests for all four results, invalid reason, stale/nonowner decisions, score/version snapshots, pending removal and ordered history; implement service, schemas, routes and app wiring and verify those tests pass.

## 3. Demonstration and verification

- [x] 3.1 Add an explicit idempotent synthetic comment seed command and `docs/backend/05-revision-e-historico.md` with a runnable claim/reveal/review/history lesson; verify command output and update README.
- [x] 3.2 Run the complete test suite, dependency check, OpenSpec validation, diff checks and a real HTTP smoke test; record results, limitations and the Jira branch exception in `evidence.md`.

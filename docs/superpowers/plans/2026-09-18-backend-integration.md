# Backend Integration Implementation Plan

> **For agentic workers:** execute these checkboxes in order. Preserve the
existing uncommitted authentication and review work in this worktree.

**Goal:** deliver a working browser-to-API moderation path with optional real-model inference.

**Architecture:** a FastAPI modular monolith serves the API and static UI.
SQLite migrations distinguish both known version-3 schemas by their columns.
The scoring boundary accepts either simulated output or a trusted local model.

**Tech Stack:** Python 3.12, FastAPI, SQLite, Pydantic, plain HTML/CSS/JS,
scikit-learn and joblib for the optional model adapter, pytest for backend checks.

**Spec:** `docs/superpowers/specs/2026-09-18-backend-integration-design.md`

## Global Constraints

Use English identifiers and Spanish learning documentation. Keep raw comments
out of queue responses, audit rows and logs. No automatic YouTube actions.
Jira was explicitly waived for this local learning work. Preserve existing
uncommitted files and avoid external writes or deployment.

---

### Task 1: Reconcile the SQLite schema and existing workflows

**Files:** `backend/app/database.py`, `backend/app/comments/repository.py`,
`backend/app/comments/schemas.py`, `backend/app/comments/router.py`,
`backend/app/comments/service.py`, `backend/tests/test_integration_storage.py`.

**Interfaces:** `Database.initialize()` produces version 5; `CommentRepository`
offers `insert_batch()` and `page()` while retaining claim, reveal, review and
history operations. Both `GET /comments` and its `/comments/queue` alias return
`QueuePage`; `/comments/status` exposes status-filtered summaries.

- [x] Test fresh version 5 schema and idempotent initialization.
- [x] Test known legacy migrations and unknown version 3 shape handling.
- [x] Port the completed step-6 modules and implement transactional upgrades.
- [x] Test supervisor import and paginated, text-free queue.
- [x] Run existing auth, review and supervision tests; update version assertions.

### Task 2: Connect the model boundary

**Files:** `backend/app/comments/scoring.py`, `backend/app/config.py`,
`backend/app/main.py`, `backend/tests/test_model_integration.py`,
`pyproject.toml`, `.env.example`.

**Interfaces:** `score_comment(text) -> Score`; `MODERATION_SCORER_MODE`
selects `simulated` or `model`; `MODERATION_MODEL_PATH` selects a trusted
artifact. API import returns 503 and writes nothing if scoring fails.

- [x] Test a tiny synthetic fitted pipeline.
- [x] Implement and verify the joblib adapter and positive class 1.
- [x] Test missing artifact and no partial import on scoring failure.
- [x] Record optional dependencies and run `pip check`.

### Task 3: Build the same-origin frontend

**Files:** `frontend/index.html`, `frontend/app.js`, `frontend/styles.css`,
`backend/app/main.py`, `backend/tests/test_frontend_contract.py`.

**Interfaces:** `/ui/` serves the page and relative `/auth`, `/comments`,
`/supervisor` requests. Tokens remain in memory. Text appears only after
`GET /comments/{id}/content` succeeds for the active assignee.

- [x] Test `/ui/` and static assets and mount them through FastAPI.
- [x] Build login, logout, queue, claim, reveal, review and history interactions using DOM `textContent` and explicit error states.
- [x] Add supervisor import, escalations, resolution, reassignment and reopen-request interactions; verify permissions with API tests.
- [x] Keep bearer token and revealed text in memory only; inspect frontend source and API response contracts.

### Task 4: Finish the integration evidence

**Files:** `docs/backend/07-integracion-completa.md`, `README.md`,
`openspec/changes/backend-integration/*`.

- [x] Run the full test suite, `pip check`, OpenSpec validation and `git diff --check`.
- [x] Start Uvicorn on loopback with isolated SQLite and verify `/ui/` plus `/health`; verify the human path with HTTP integration tests.
- [x] Record absent raw data/artifact and the synthetic fixture's evidence limit.
- [x] Mark supported OpenSpec tasks complete.

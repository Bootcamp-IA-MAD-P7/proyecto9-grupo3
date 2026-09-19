# Tasks

## 1. Persistence

- [x] 1.1 Add failing migration and state-transition tests, then implement SQLite version 4 with request/action tables and assignment return state and expanded text-free audit; verify old rows survive and tests pass.

## 2. Supervisor operations

- [x] 2.1 Add tests and implement supervisor escalation listing, resolution and reassignment, including role and concurrency errors; verify status, ownership and append-only history.

## 3. Reopening operations

- [x] 3.1 Add tests and implement staff request, duplicate prevention, supervisor approval/rejection and information exchange; verify no premature queue return and prior review preservation.

## 4. Documentation and verification

- [x] 4.1 Add a Spanish learning guide for the state machine, migration and HTTP examples; verify example requests against the API.
- [x] 4.2 Run the full test suite, dependency check, OpenSpec validation, harness, diff check and live HTTP smoke; record evidence and any Jira exception.

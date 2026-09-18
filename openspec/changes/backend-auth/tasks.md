# Tasks

## 1. Authentication persistence and primitives

- [x] 1.1 Add failing tests for demo users, salted hashes, schema preservation and secret-free storage in `backend/tests/test_auth.py`; run them before implementing `database.py`, `auth/models.py`, `auth/security.py`, `auth/repository.py` and `seed_demo_users.py`, then verify these tests pass.
- [x] 1.2 Add pwdlib Argon2 dependencies and validated database/session/throttle settings; verify environment installation with `pip check` and invalid settings tests.

## 2. HTTP authentication and authorization

- [x] 2.1 Write failing login/me/logout tests, then implement schemas, service, router, lifespan integration and dependencies; verify successful logins, generic 401, expiration, revocation and cross-instance persistence.
- [x] 2.2 Verify the role guard using a test-only route: moderator 403, supervisor 200, anonymous 401, forged role no elevation and stored role changes applied immediately.
- [x] 2.3 Verify persistent throttling, cache headers and redacted validation errors using real HTTP tests and captured logs; implement the minimal controls to pass them.

## 3. Learning and evidence

- [x] 3.1 Write the step 3 learning guide with setup, hidden demo password prompts, Swagger login/me/logout exercises and the 401/403 distinction; update README and environment example and verify the documented commands.
- [x] 3.2 Run the complete suite, pip check, strict OpenSpec validation, diff checks and a real Uvicorn auth smoke test; obtain independent review, address findings and record evidence and the Jira exception.

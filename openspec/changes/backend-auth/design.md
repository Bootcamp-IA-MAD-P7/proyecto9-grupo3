# Design

## Context

See proposal.md and specs/backend-auth/spec.md. The user explicitly requested
step 3 and previously waived Jira. The integrated branch already has the
step-2 SQLite schema for users and comments. This change migrates it to add auth.

## Decisions

### Opaque server sessions

Use random 32-byte URL-safe tokens with SHA-256 digests stored in SQLite. Each
request resolves the session and active user, so revocation and role changes are
immediate. JWT was considered, but requires signing-key lifecycle and extra
revocation mechanisms that are unnecessary for this single-process demo design.
Sessions also work across local instances sharing the database. Bearer tokens
must be kept in frontend memory and sent over HTTPS outside loopback development.

### Password hashing

Use pwdlib's recommended Argon2id hasher. Never store or log plaintext passwords.
Verify against a dummy hash for unknown users to avoid an obvious timing shortcut.
Demo passwords are supplied through getpass or process environment, not default
credentials committed to Git. No secrets are embedded in OpenAPI examples.

### Version 2 SQLite authentication migration

`users` and `comments` already exist in version 1. Existing users have UUID id,
unique normalized username, display_name, password_hash, role and active flag.
`sessions`: token_hash primary key, user foreign key, created/expires timestamps.
`login_attempts`: normalized username primary key, attempts, window start.

Use stdlib sqlite3, parameterized SQL, foreign keys and a connection per operation.
Version 1 to 2 migration uses a transaction and `PRAGMA user_version`, preserving
users and comments. Reject newer
versions. Session cleanup occurs on login. Login counters use a short IMMEDIATE
transaction so concurrent attempts cannot evade the counter. Hashing occurs
outside the write transaction. Limit is per username; network-wide controls are
a separate deployment concern.

### Responsibilities

| File | Responsibility |
| --- | --- |
| `app/database.py` | Connections, constraints and schema initialization |
| `app/auth/models.py` | Role enum and internal immutable user record |
| `app/auth/schemas.py` | Public API input/output models |
| `app/auth/security.py` | Password verification and token digest operations |
| `app/auth/repository.py` | Parameterized user/session/throttle queries |
| `app/auth/service.py` | Login, expiry, logout and session resolution |
| `app/auth/dependencies.py` | FastAPI authentication and role guard |
| `app/auth/router.py` | Three HTTP endpoints and response codes |
| `app/errors.py` | Validation error responses without submitted values |
| `app/seed_demo_users.py` | Explicit local demo provisioning |

FastAPI startup initializes the database through lifespan. App construction
validates settings and wires dependencies. Role guards are exercised on a
test-only protected route; no fictitious supervisor moderation endpoint is added.
Future business routes must attach the guard individually.

### Authentication errors and input bounds

Limit login username to 64 characters and password to 1024, reject extra fields,
and normalize usernames by trimming and lowercasing. Use HTTPBearer with
auto_error=False so absent/invalid tokens get a deliberate 401. Only generated
URL-safe token shapes are looked up. Invalid role values are rejected by SQLite.
Return sanitized validation details and never the input object. Auth responses,
including errors, receive no-store headers through a narrowly scoped middleware.

## Risks / Trade-offs

- SQLite is suitable for the learning/demo scope; multi-host deployment requires
  a shared database and migration design.
- Per-username throttling permits temporary targeted lockout and does not replace
  reverse-proxy/global abuse controls. Document it as a demo limitation.
- No user management/reset endpoint exists; demo seeding never overwrites users.
- Argon2 is deliberately costly; tests use actual hashing and temporary databases.
- No deployment, merge or external moderation is part of this work.

## Verification and rollback

Write failing HTTP/security/persistence tests first. Test real SQLite, hashes,
expiry, revocation, current role, malicious inputs and cross-instance sessions.
Run the foundation/harness unit suites, OpenSpec validation and a real HTTP smoke
test with synthetic credentials in a temporary database. Review independently.
Rollback stops the local API and reverts this change; the ignored local database
is retained. Never automatically delete a user's database.

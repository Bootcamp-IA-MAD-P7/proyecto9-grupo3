# Spec Delta

## Purpose

Let demo moderators and supervisors establish revocable sessions and enforce
server-owned roles before comment moderation operations are implemented.

## ADDED Requirements

### Requirement: Credentials establish bounded sessions
`POST /auth/login` SHALL accept a JSON username and password and return HTTP 200
with `access_token`, `token_type=bearer`, `expires_in` and a public user containing
only id, username, display_name and role. Sessions SHALL expire after 1800 seconds
by default, configurable from 60 to 86400 seconds. Wrong passwords, unknown users
and inactive users SHALL receive the same HTTP 401 response.

#### Scenario: A demo user logs in
- **WHEN** correct credentials for an active user are submitted
- **THEN** a new random token and its lifetime are returned without the password or hash

#### Scenario: Credentials cannot authenticate
- **WHEN** a password is incorrect, a username is unknown or a user is inactive
- **THEN** the API returns 401 with the same generic error and creates no session

### Requirement: Sessions persist and can be revoked
`GET /auth/me` SHALL require an Authorization Bearer token and return the current
public user. Missing, malformed, expired, revoked or unrecognized tokens and
tokens for inactive users MUST produce 401 with `WWW-Authenticate: Bearer`.
Tokens MUST only be accepted through the Authorization header. `POST /auth/logout`
SHALL revoke the authenticated session and return 204. Other sessions SHALL remain valid.

#### Scenario: Application restarts
- **WHEN** another app instance uses the same database and receives an unexpired token
- **THEN** it recognizes the session and returns the user

#### Scenario: Token is unusable
- **WHEN** a token is missing, malformed, expired, revoked or belongs to an inactive user
- **THEN** protected access returns 401

#### Scenario: A user logs out
- **WHEN** an authenticated user logs out
- **THEN** that token becomes unusable immediately and another session remains valid

### Requirement: Roles are owned by the server
Users SHALL have exactly MODERATOR or SUPERVISOR as a stored role. Protected
operations SHALL use a reusable role guard that returns 403 for an authenticated
user outside the allowed set. Role changes in storage SHALL affect existing
sessions on the next request. Login MUST reject additional fields, including role.

#### Scenario: Moderator tries a supervisor-only operation
- **WHEN** a MODERATOR calls an operation guarded for SUPERVISOR
- **THEN** the guard returns 403, while a SUPERVISOR can perform the same operation

#### Scenario: Client claims a privileged role
- **WHEN** a caller sends a role in the login body, a query or a custom header
- **THEN** no server-side permission is elevated

#### Scenario: Role changes after login
- **WHEN** a user's stored role changes while its session is valid
- **THEN** subsequent authorization uses the current stored role

### Requirement: Secrets are protected at rest and in errors
Passwords MUST be stored as salted Argon2id hashes; sessions MUST store only a
SHA-256 digest of a cryptographically random token with at least 256 bits of
entropy. Login and authenticated responses SHALL include `Cache-Control: no-store`.
Validation errors MUST omit submitted inputs, and application logs MUST NOT
include passwords, password hashes or tokens.

#### Scenario: Stored credentials are inspected
- **WHEN** two demo users have the same password
- **THEN** their stored Argon2id hashes differ and neither stored value is the password

#### Scenario: Invalid input contains a secret
- **WHEN** login validation rejects a body containing a password
- **THEN** the error response and application logs do not repeat that password

### Requirement: Login attempts are bounded
Login SHALL limit requests per normalized username to five attempts per 60-second
window by default, persisting counters across app instances. Attempts beyond the
limit SHALL receive 429 and Retry-After. A successful login SHALL clear its counter.

#### Scenario: Repeated login failures
- **WHEN** the limit has been reached for a username in the active window
- **THEN** further attempts receive 429 until that window expires

### Requirement: Demo provisioning is explicit and repeatable
A local command SHALL migrate the version-1 SQLite persistence schema to version 2
and create moderator and supervisor demo users using passwords supplied locally
through hidden prompts or environment variables. Passwords SHALL be 12 to 1024
characters. Repeated seeding MUST preserve existing users and passwords.
Schema initialization SHALL preserve existing users and comments and reject newer schema
versions without changing them. No public registration or user management route
SHALL be introduced.

#### Scenario: Demo command is repeated
- **WHEN** valid demo passwords are supplied and the command runs twice
- **THEN** only the two intended users exist and their original credentials remain valid

#### Scenario: Unsupported future schema is encountered
- **WHEN** the database schema version is newer than supported
- **THEN** initialization fails without overwriting existing data

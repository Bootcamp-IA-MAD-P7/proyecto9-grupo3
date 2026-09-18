# Authentication verification

Original implementation: 2026-09-18, Python 3.12.10, Windows,
`feature/backend-auth`. Integrated into `feature/backend-steps-1-4` after the
user chose SQLite direct access for all four steps.

## Automated evidence

| Check | Result |
| --- | --- |
| Initial focused HTTP contract test | Failed: login returned 404 instead of the expected 401 for an unknown user |
| Initial auth suite | 6 failures and 26 setup errors due to absent authentication modules/settings |
| Complete final suite | 63 passed, including 35 auth cases, plus 6 unittest subtests |
| `python -m pip check` | No broken requirements found |
| Strict OpenSpec validation | `backend-auth` is valid |
| `git diff --check` | No whitespace errors |
| Repository harness | Only failure: branch name lacks the Jira SP key, explicitly waived by the user |

Test command: `.venv/Scripts/python.exe -m pytest -q --tb=short
--basetemp=.pytest_cache/auth-temp`. The suite continues to expose two existing
dependency warnings (Starlette HTTPX migration and deprecated AnyIO portal alias).
They are not suppressed and did not cause failures.

## Real HTTP and CLI evidence

Used a temporary SQLite database and random synthetic passwords passed through
child-process environment variables; no passwords or tokens were printed.

1. Ran `python -m app.seed_demo_users` twice successfully, preserving the users.
2. Started a real Uvicorn process on loopback; anonymous `/auth/me` returned 401.
3. Logged in as moderator and supervisor; both returned 200 and their expected roles.
4. Stopped and restarted the process using the same temporary database.
5. Both tokens remained usable after restart.
6. Moderator logout returned 204; reusing that token returned 401.
7. The supervisor's separate session still returned 200.
8. Checked server output for the passwords and tokens: none were present.
9. Stopped both test processes and removed only their isolated temporary data.

The default developer database has not been provisioned with automatic or known
passwords. The learner chooses those using the documented hidden prompt command.

## Integrated four-step branch

After the user's SQLite decision, the step-3 commit was rebuilt on top of the
step-2 users/comments schema. The focused foundation, persistence and auth suite
passed: 48 tests. A new migration test checked that version 1 users and comments
survive the version 2 upgrade. Strict OpenSpec validation and `git diff --check`
passed. The original standalone evidence above remains historical context.

## Independent review

A read-only reviewer examined the implementation, spec and tests and identified:

- Client-controlled extra-field names could be echoed in validation error locations.
- Unpaired Unicode surrogates in password strings could cause an internal error.

Reproduced both with three failing tests. The error handler now preserves only
trusted request-source names. Password validation rejects malformed UTF-8 before
hashing. The reviewer independently reran the three regression cases and confirmed
both findings resolved, with no unresolved issue from its original review.

## Scope and remaining work

Role guards are verified on a test-only supervisor route; real supervisory
moderation operations belong to later increments and will require those guards.
The integrated branch retains users and comments from step 2 and adds sessions
and login attempts through schema version 2. This is a local demo implementation; deployment,
HTTPS termination and network-wide abuse controls require a separate design.

Jira enforcement remains unchanged in the repository; the failure is recorded
instead of hidden. No team merge approval, commit, push, deployment or OpenSpec
archive is claimed by these results.

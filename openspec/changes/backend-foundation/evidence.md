# Evidence: backend foundation

Date: 2026-09-17. Environment: Windows, Python 3.12.10.
Branch: `feature/backend-foundation`. Jira omitted by explicit user instruction.

## Behavior and verification

| Check | Result |
| --- | --- |
| First behavioral test run after resolving temp-directory permissions | 9 failures because the `app` implementation did not exist |
| `python -m pytest -q --basetemp=.pytest_cache/foundation-temp` | 28 passed, including 9 backend cases; 6 unittest subtests passed |
| `python -m pip check` | No broken requirements found |
| Real Uvicorn process, `GET /health` | HTTP 200, JSON `{"status":"ok"}` |
| Real Uvicorn process, `GET /docs` | HTTP 200, HTML served |
| Real Uvicorn process, `GET /openapi.json` | HTTP 200, title and health route verified |
| `openspec validate backend-foundation --strict` | Valid |
| `git diff --check` | No whitespace errors in the tracked diff |
| `python scripts/validate_harness.py` | Fails only the branch-name requirement for a Jira SP key |

The smoke server used an available loopback port and was stopped afterward.
The browser rendering of Swagger CDN assets was not part of the HTTP smoke
check. The learner can start the server on port 8000 using the guide.

## Scenario mapping

- Health/liveness: `test_health_is_public_and_only_reports_process_liveness`.
- OpenAPI response schema: `test_openapi_describes_the_health_response`.
- Local docs: `test_interactive_docs_are_available_for_local_learning`.
- Docs disabled: three parameter cases of
  `test_documentation_can_be_disabled_without_disabling_health`.
- Environment title: `test_app_title_uses_environment_configuration`.
- Invalid configuration: `test_invalid_configuration_fails_before_serving_requests`.
- File settings and shell precedence:
  `test_dotenv_is_optional_and_shell_values_take_precedence`.

## Limitations and follow-up

The test run reports two dependency deprecation warnings: Starlette's TestClient
currently recommends HTTPX2, and its AnyIO BlockingPortal import uses a deprecated
alias. They originate in dependencies, are not suppressed, and do not fail the
verified tests. Revisit these dependencies when the integration changes.

The existing harness remains intact. Its Jira branch restriction is an explicit
exception for this local work, not a passing check or permission to merge.
No independent teammate review, commit, push, merge, deployment or archive was
performed. Moderation, persistence and authentication are future increments,
listed in the learning guide; this evidence does not claim the full backend is done.

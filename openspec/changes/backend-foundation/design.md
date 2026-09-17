# Design

## Context

See `proposal.md` for motivation and authorization to omit Jira for this work.
The repository has no runtime application. Python 3.12 is available locally.
The learner wants executable increments and an explanation of each component.

## Goals / Non-Goals

**Goals:** keep one runnable process, a small explicit configuration surface,
typed HTTP responses, an inspectable contract and fast isolated tests.

**Non-goals:** introduce empty service/repository layers, database tables,
authentication, cloud services or inferred moderation policy in this increment.

## Decisions

### One Python application using FastAPI

Python fits the project's future model pipeline. FastAPI provides typed
request/response contracts and OpenAPI generation. Uvicorn serves the app.
Flask would require choosing additional schema/documentation tools. Django
would provide useful administration features, but the proposed MVP explicitly
excludes user administration and public registration. Both are viable later
alternatives; FastAPI fits this small API and short delivery window.

The intended architecture is a modular monolith. Add services for moderation
rules and repositories for persistence when those behaviors are implemented.
Do not create unused abstractions now.

### Create the app through a factory

`backend/app/main.py` exposes `create_app() -> FastAPI`. It loads `Settings`,
configures documentation URLs and includes the health router. Uvicorn invokes
it with `app.main:create_app --factory`. This makes each test app independent
and avoids loading configuration as an import side effect.

### Keep code close to its responsibility

| File | Responsibility |
| --- | --- |
| `backend/app/main.py` | Assemble a fresh application |
| `backend/app/config.py` | Validate name and documentation settings |
| `backend/app/health.py` | Health route and its tiny response schema |
| `backend/tests/test_foundation.py` | Verify the public contract and configuration behavior |
| `pyproject.toml` | Package dependencies, source layout and pytest discovery |
| `docs/backend/01-primer-endpoint.md` | Reproducible learning guide and roadmap |

The health schema remains next to its route because it has no shared consumers
in this increment. Separate domain schemas when the domain appears.

### Validate environment settings

Pydantic Settings reads `MODERATION_APP_NAME` (default `Moderation API`, nonempty)
and `MODERATION_DOCS_ENABLED` (default true). It optionally reads `.env` from the
working directory, which is the repository root in documented commands. It
ignores unrelated keys in that file. Shell variables override file values.
Invalid values stop startup. Secrets and `.env` remain excluded from Git.

### Health is liveness

`GET /health` returns only a typed status `ok`. It does not load data, call a
model or make outbound requests. A future readiness endpoint can check required
dependencies without changing the meaning of liveness.

## Risks / Trade-offs

- [Learner mistakes this for a completed backend] -> Mark delivered and future
  capabilities explicitly in the guide and README.
- [Swagger assets require internet] -> Document that `/openapi.json` remains
  directly inspectable without loading the Swagger browser assets.
- [Unreviewed dependency updates] -> Record tested dependency versions in a
  constraints file alongside compatible direct requirements in `pyproject.toml`.
- [No Jira identifier] -> Record the explicit user exception and report the
  existing branch-name harness failure separately; do not weaken its rules.
- [Conflict in future reopening behavior] -> Preserve the existing SP-2
  contract and document the discrepancy until the reopening increment is designed.
- [Raw data leakage] -> This increment reads no dataset and introduces no
  comment logging. Subsequent increments must preserve that boundary.

## Migration Plan

Create the local `.venv`, install the editable project with development extras,
and run Uvicorn bound to `127.0.0.1`. Verify tests, package consistency and a real
HTTP request. No deployment or database migration occurs. Rollback is stopping
the local server and reverting this increment's files on the feature branch.

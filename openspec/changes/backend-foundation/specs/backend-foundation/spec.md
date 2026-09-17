# Spec Delta

## Purpose

Provide an executable local API foundation so developers can learn, inspect and
verify the request-response contract before adding comment moderation features.

## ADDED Requirements

### Requirement: Process liveness is observable
The API SHALL expose unauthenticated `GET /health`, returning HTTP 200 with
exactly `{"status":"ok"}` as JSON while the process is serving requests.
This response MUST describe process liveness only and MUST NOT claim database
readiness, model availability or moderation completeness.

#### Scenario: Developer checks the running process
- **WHEN** a developer requests `GET /health` without credentials
- **THEN** the API returns HTTP 200 and the JSON object `{"status":"ok"}`

### Requirement: The API contract is inspectable
In the default local configuration, the API SHALL serve its OpenAPI description
at `/openapi.json` and interactive documentation at `/docs`. The description
SHALL document the health endpoint and its JSON response schema.

#### Scenario: Developer inspects the first endpoint
- **WHEN** a developer requests `/openapi.json` using default configuration
- **THEN** the API returns HTTP 200 and a schema describing `GET /health` with a JSON response whose status is `ok`

#### Scenario: Developer opens the local documentation
- **WHEN** a developer opens `/docs` using default configuration
- **THEN** the API returns HTTP 200 and the documentation HTML page

### Requirement: Configuration controls documentation
The API SHALL read `MODERATION_APP_NAME` and `MODERATION_DOCS_ENABLED` at app
creation, supporting environment variables and an optional `.env` file in the
working directory. Shell variables SHALL take precedence over `.env` values.
Invalid configuration MUST fail app creation before serving requests.

#### Scenario: Documentation is disabled
- **WHEN** `MODERATION_DOCS_ENABLED=false` and the app starts
- **THEN** `/docs`, `/redoc` and `/openapi.json` return HTTP 404 while `/health` remains available

#### Scenario: Developer changes the application title
- **WHEN** `MODERATION_APP_NAME=Teaching API` and the app starts
- **THEN** the OpenAPI title is `Teaching API`

#### Scenario: Environment overrides a local settings file
- **WHEN** `.env` sets the application title to `File API` and the shell sets it to `Shell API`
- **THEN** the OpenAPI title is `Shell API`

#### Scenario: Documentation flag is invalid
- **WHEN** `MODERATION_DOCS_ENABLED=not-a-boolean` and app creation is attempted
- **THEN** configuration validation fails and the app does not start serving requests

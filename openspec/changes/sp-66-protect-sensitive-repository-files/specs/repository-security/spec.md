## ADDED Requirements

### Requirement: Sensitive paths are not tracked

The repository harness SHALL reject tracked `.env` variants except `.env.example`,
obvious key or credential filenames, and reserved local real-data directories.

#### Scenario: A sensitive path is present

- **WHEN** a tracked path is `.env`, `config/.env.local`, `credentials.json`,
  `private.key`, or under `data/raw/`
- **THEN** harness validation fails with a sensitive-path error

#### Scenario: An example or normal path is present

- **WHEN** a path is `.env.example` or `docs/README.md`
- **THEN** the sensitive-path check passes

### Requirement: The control has bounded scope

The harness SHALL validate names and paths only. It SHALL NOT inspect contents,
claim to detect every secret, or add external secret-management tooling.

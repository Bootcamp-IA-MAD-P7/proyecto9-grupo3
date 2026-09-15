## ADDED Requirements

### Requirement: Integration uses squash merge only

Every PR integrated into `dev` or `main` SHALL use squash merge. GitHub SHALL
allow squash merge and SHALL disable merge commit and rebase merge. The final
squash commit SHALL be represented by the PR title's Conventional Commit format.

#### Scenario: A focused Jira PR is approved into dev

- **WHEN** an approved PR with green checks is integrated into `dev`
- **THEN** GitHub offers squash merge as the only merge strategy
- **AND** the resulting commit has a linear, traceable relationship to the PR

#### Scenario: An accepted release is promoted to main

- **WHEN** an approved release PR promotes `dev` into `main`
- **THEN** the same squash-only strategy applies
- **AND** `main` retains linear history

### Requirement: Merge strategy does not alter other gates

The squash-only policy SHALL NOT replace approval, required-check, release, or
tag requirements.

#### Scenario: A PR lacks approval or a green check

- **WHEN** a PR does not meet an independent gate
- **THEN** squash merge availability does not authorize its integration

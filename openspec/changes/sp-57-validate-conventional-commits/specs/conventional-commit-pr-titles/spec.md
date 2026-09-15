## ADDED Requirements

### Requirement: Pull-request titles use the approved Conventional Commit format

On a pull-request event, the repository harness SHALL require the PR title to
match `^(feat|fix|docs|test|ci|chore)(\([a-z0-9][a-z0-9-]*\))?!?: [a-z0-9].+$`.
The rule SHALL apply to work PRs and release PRs. Jira traceability SHALL remain
independently required in the branch, title, or body.

#### Scenario: A focused work PR has a valid title

- **WHEN** a PR title is `feat: add toxicity prediction endpoint`
- **THEN** the Conventional Commit title check passes
- **AND** the existing Jira, OpenSpec, and branch checks still run

#### Scenario: A title uses an unsupported type or invalid structure

- **WHEN** a PR title uses an unsupported type, lacks `:`, or starts its
  description with an uppercase letter
- **THEN** the harness fails with an actionable Conventional Commits message

#### Scenario: A release PR is reviewed

- **WHEN** `dev` opens a PR into `main` with a compliant Conventional Commit title
- **THEN** the title check passes
- **AND** source-branch and source-repository validation still apply

### Requirement: The automated rule has a bounded purpose

The harness SHALL validate PR-title structure only. It SHALL NOT rewrite titles,
inspect intermediate commits, or claim that a description is English.

#### Scenario: A reviewer evaluates wording quality

- **WHEN** a structurally valid title needs language or semantic review
- **THEN** the automated check does not claim to validate that quality
- **AND** the reviewer retains responsibility for it

## ADDED Requirements

### Requirement: Pull requests use a standard evidence-first template

The repository SHALL provide one English PR template with sections for context
and traceability, what changes and why, acceptance criteria, validation,
data/security/operations, risks/decisions/rollback, and review. Each PR body
SHALL include a Jira field containing an `SP-<number>` key.

#### Scenario: A contributor opens a work PR

- **WHEN** a contributor opens a PR
- **THEN** the template makes Jira, outcome, acceptance criteria, validation,
  risk, rollback, and reviewer evidence visible
- **AND** the harness accepts the Jira field when it contains an `SP-<number>` key

### Requirement: OpenSpec traceability is explicit and proportionate

Each PR body SHALL include an OpenSpec field. The field SHALL link an
existing `openspec/changes/<lowercase-kebab-case-change>/` repository path for
a material change, or use
`N/A — <non-empty reason>` for a non-material change. The harness SHALL reject
a missing field, an invalid or nonexistent path, or an unexplained `N/A`; an
independent reviewer SHALL assess whether a non-material justification is
appropriate.

#### Scenario: A material harness change is proposed

- **WHEN** a PR changes user behavior, data, model, API, security, deployment,
  or harness rules
- **THEN** its OpenSpec field links the relevant `openspec/changes/` directory

#### Scenario: A documentation-only clarification is proposed

- **WHEN** a PR is non-material
- **THEN** its OpenSpec field may state `N/A — documentation-only clarification`
- **AND** the reviewer can assess that declaration

#### Scenario: A PR omits OpenSpec context

- **WHEN** a PR body lacks the OpenSpec field or gives `N/A` without a reason
- **THEN** the harness fails with an actionable message

#### Scenario: An OpenSpec value is not a repository path

- **WHEN** the OpenSpec field contains arbitrary text, an incomplete path, an
  external link, or a nonexistent change directory
- **THEN** the harness rejects the value as invalid OpenSpec traceability

### Requirement: Existing gates remain independent

The template rule SHALL NOT replace branch naming, Jira traceability, Conventional
Commit titles, release-source checks, independent review, or acceptance evidence.

#### Scenario: A title and template field are both invalid

- **WHEN** a PR has an invalid title and missing OpenSpec field
- **THEN** the harness reports both failures

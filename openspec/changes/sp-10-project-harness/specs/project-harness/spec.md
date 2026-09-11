## ADDED Requirements

### Requirement: Traceable work

Every material repository change SHALL be linked to a Jira work item and SHALL
use the Jira key in its branch and pull request.

#### Scenario: A contributor starts material work

- **WHEN** a contributor begins a feature, fix, infrastructure, or harness change
- **THEN** the contributor identifies the Jira key before implementation
- **AND** works on a branch whose name contains that key

### Requirement: Collaborative specification gate

Changes to user-visible behavior, data or model behavior, public interfaces,
security, or deployment SHALL have an accepted OpenSpec change before production
implementation begins.

#### Scenario: The Jira story is incomplete

- **WHEN** the team or an agent finds ambiguous scope or unverifiable criteria
- **THEN** it presents questions and a proposed enrichment separately
- **AND** does not silently write the proposal back to Jira or implement it

### Requirement: Independent evidence

A change SHALL not be considered done until its acceptance criteria are mapped to
tests or reviewable evidence and a contributor other than the author has reviewed
it.

#### Scenario: Automated checks pass but evidence is incomplete

- **WHEN** tests pass but one acceptance criterion has no evidence
- **THEN** the change remains incomplete

### Requirement: Safe uncertainty handling

The moderation product SHALL distinguish a negative prediction from a harmful
content decision and SHALL abstain when the available evidence is insufficient.

#### Scenario: A comment is context-dependent

- **WHEN** an isolated comment cannot be classified responsibly without its
  conversational context
- **THEN** the system reports insufficient context
- **AND** recommends human review instead of asserting harmful intent

### Requirement: Human control of external actions

The project SHALL require explicit human confirmation before any action that
changes content or author status on an external platform.

#### Scenario: YouTube moderation is proposed

- **WHEN** the system recommends rejecting a comment or banning an author
- **THEN** it produces a reviewable recommendation or report
- **AND** does not perform the YouTube action without explicit authorization and
  confirmation by an authorized human

### Requirement: Repository quality gate

The repository SHALL provide an automated, dependency-light validation of its
harness structure and pull-request traceability.

#### Scenario: A pull request omits its Jira key

- **WHEN** a pull request branch or description has no `SP-<number>` reference
- **THEN** the harness check fails with an actionable explanation


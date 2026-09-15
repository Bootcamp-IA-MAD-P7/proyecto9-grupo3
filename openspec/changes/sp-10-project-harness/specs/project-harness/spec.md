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

### Requirement: Integration and release branches have distinct roles

Material work SHALL branch from and return to `dev`. Authorized early AWS demo
deployments SHALL use `dev` as their source. The `main` branch SHALL be reserved
for the accepted final production-ready release promoted from `dev`.

#### Scenario: A contributor opens a feature pull request

- **WHEN** material work is ready for team review
- **THEN** its pull request targets `dev`
- **AND** required checks and independent approval apply before merge

#### Scenario: The team prepares the final release

- **WHEN** the integrated release on `dev` has been accepted
- **THEN** the team promotes that release to protected `main`

### Requirement: Independent evidence

A change SHALL not be considered done until its acceptance criteria are mapped to
tests or reviewable evidence and a contributor other than the author has reviewed
it.

#### Scenario: Automated checks pass but evidence is incomplete

- **WHEN** tests pass but one acceptance criterion has no evidence
- **THEN** the change remains incomplete

### Requirement: Product hypotheses remain non-binding

The harness SHALL distinguish accepted team decisions from unvalidated product
or architecture hypotheses. English as the initial language, abstention under
uncertainty, and the AWS architecture are currently hypotheses and SHALL NOT be
treated as mandatory implementation requirements.

#### Scenario: A hypothesis is recorded before validation

- **WHEN** the team records a proposed language, uncertainty behavior, or AWS
  architecture without sufficient product or technical evidence
- **THEN** the proposal is explicitly labeled as a hypothesis
- **AND** implementation is not blocked by treating it as an accepted requirement

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

# Backend Integration Specification

## ADDED Requirements

### Requirement: Compatible persistence

The backend SHALL initialize schema version 5 and migrate known auth, review,
supervision and dev queue database versions without losing stored users,
comments, assignments or reviews. It SHALL reject unknown version 3 shapes
without changing them.

#### Scenario: Existing dev queue

- **WHEN** a version 3 queue database has scored comments
- **THEN** initialization preserves their identifiers, order, text and scoring metadata

#### Scenario: Legacy active assignment

- **WHEN** a version 3 queue database has an in-review comment with an assignee
- **THEN** initialization preserves that assignee with a fresh finite claim lease

### Requirement: Import and queue

Only supervisors SHALL import validated batches. The batch SHALL be atomic.
Authenticated reviewers SHALL see a paginated pending queue ordered by score
and source order; the queue SHALL omit stored text.

#### Scenario: Import and review

- **WHEN** a supervisor imports synthetic comments and a reviewer claims one
- **THEN** only its assignee can reveal text and save a human review
- **AND** the resulting history records the decision without comment text

### Requirement: Selectable scoring

The application SHALL support explicit simulated or model scoring. Model mode
SHALL require a trusted local artifact and expose score source and version.
Unavailable scoring SHALL leave import data unchanged.

#### Scenario: Missing model artifact

- **WHEN** model mode names an artifact that does not exist
- **THEN** application startup fails without switching to simulated mode

#### Scenario: Scoring fails during a batch

- **WHEN** scoring fails for any item in an import batch
- **THEN** the API returns an unavailable response and inserts no item

### Requirement: Browser integration

The same-origin `/ui/` SHALL support login, queue, claim, reveal, review,
history, import and supervisor actions with permission feedback. It SHALL keep
tokens in memory and render server-provided strings as text.

#### Scenario: Browser review

- **WHEN** a signed-in reviewer claims a pending comment
- **THEN** the browser can reveal its text and submit a human decision
- **AND** a fresh page load requires a new login

#### Scenario: Resume and inspect

- **WHEN** a reviewer logs in after refreshing the page
- **THEN** the browser lists that reviewer's active assignments
- **AND** the reviewer can consult history by comment ID after a decision

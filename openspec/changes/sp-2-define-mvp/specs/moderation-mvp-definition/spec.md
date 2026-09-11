## Purpose

Define an evidence-backed MVP contract that helps a YouTube moderator decide
which dataset comment to review first without confusing model output with a
human moderation decision.

## ADDED Requirements

### Requirement: Prioritized review queue is the primary journey
The MVP SHALL present dataset comments in a review queue ordered from highest to
lowest estimated probability of the `IsToxic` target. An individual pasted
comment SHALL be a secondary journey and SHALL NOT replace the queue.

#### Scenario: Moderator opens a scored queue
- **WHEN** the dataset contains multiple comments with model scores
- **THEN** the comment with the highest estimated `IsToxic` probability appears first

#### Scenario: Moderator analyzes one pasted comment
- **WHEN** the moderator enters a non-empty comment through the secondary journey
- **THEN** the system returns an analysis without removing or replacing the queue workflow

### Requirement: Model output uses accurate product language
The MVP SHALL describe its output as an estimate of toxicity risk for the
`IsToxic` target. It MUST NOT describe that estimate as sentiment, severity,
proof of a policy violation, or certainty about the author's intent.

#### Scenario: Toxicity estimate is displayed
- **WHEN** the system displays a prediction for a comment
- **THEN** it identifies the target as toxicity and presents the score as an estimate rather than a fact

#### Scenario: A comment lacks sufficient evidence
- **WHEN** the available text does not support a reliable interpretation
- **THEN** the interface does not invent an intent or policy violation and keeps the decision with the moderator

### Requirement: Human retains moderation control
The MVP SHALL only support review and recommendation inside the product. It MUST
NOT automatically delete, reject, report, or otherwise act on YouTube content or
authors.

#### Scenario: Moderator reviews a high-risk result
- **WHEN** a high-risk comment is shown to the moderator
- **THEN** the system offers a human review decision and performs no external YouTube action

### Requirement: Core UX states are reviewable
The primary journey SHALL have observable loading, success, empty, and error
states. A model or data failure MUST NOT be presented as an empty or successful
queue.

#### Scenario: Queue loads successfully
- **WHEN** scored comments are available
- **THEN** the moderator sees the prioritized queue and can inspect a comment's result

#### Scenario: Dataset has no reviewable comments
- **WHEN** the data source returns no comments
- **THEN** the moderator sees an empty state that explains there is nothing to review

#### Scenario: Queue cannot be scored or loaded
- **WHEN** the data or model operation fails
- **THEN** the moderator sees an error state and no fabricated ranking

#### Scenario: Queue is being prepared
- **WHEN** data or model results are still pending
- **THEN** the moderator sees a loading state that does not imply completion

### Requirement: Dataset limits accompany product claims
Project evidence SHALL identify the dataset's provenance, period, topic,
language, label distribution, duplicate risk, and grouping by video. Evaluation
claims MUST NOT imply generalization beyond evidence from this source.

#### Scenario: Team reviews the dataset evidence
- **WHEN** a contributor uses the dataset to justify an MVP or model decision
- **THEN** the dataset card states that it contains 1,000 English YouTube comments from 13 Ferguson-related videos and records known label limitations

#### Scenario: Evaluation split is designed
- **WHEN** a downstream story defines train and evaluation partitions
- **THEN** comments from the same `VideoId` are kept together or the alternative and its leakage risk are explicitly justified

### Requirement: Success measures distinguish evidence from hypotheses
The MVP definition SHALL include product, UX, model, safety, operational, and
team-learning measures. Any numeric target without observed baseline evidence
MUST be labelled as a hypothesis pending validation.

#### Scenario: An unvalidated target is documented
- **WHEN** the team proposes a numeric success threshold before measuring a baseline
- **THEN** the documentation labels the threshold as a hypothesis and names how it will be tested

#### Scenario: Model quality is reported
- **WHEN** a downstream model is evaluated
- **THEN** evidence includes class-aware metrics and error analysis rather than accuracy alone

# Spec Delta

## ADDED Requirements

### Requirement: Validated atomic comment ingestion

`POST /comments/import` SHALL require a valid SUPERVISOR session and accept 1 to
1000 JSON items with nonempty `comment_id`, `video_id`, and `text`. IDs SHALL be at
most 128 characters and text at most 5000 characters. Unknown fields, repeated
IDs in a request, and blank values SHALL receive 422. Existing IDs SHALL receive
409. Either every item is stored or none is. Successful response SHALL be 201
with only an imported count.

#### Scenario: One invalid item in a batch

- **WHEN** a batch contains a blank text, repeated ID, or ID already stored
- **THEN** no item from that batch is persisted

### Requirement: Explicit simulated scoring boundary

Each accepted item SHALL receive a deterministic score in [0, 1], an uncertainty
value, a model version, and a source label. The initial adapter SHALL mark all
scores `SIMULATED`, version `simulated-v1`, uncertainty 1.0. It SHALL make no
toxicity accuracy or probability claim. If scoring fails, import SHALL return
503 and store no item.

#### Scenario: Scoring is unavailable

- **WHEN** the scoring adapter fails during import
- **THEN** the API returns 503, never an empty successful queue or partial batch

### Requirement: Private and stable paginated queue

`GET /comments` SHALL require MODERATOR or SUPERVISOR. It SHALL return pending
comments ordered by descending score then original insertion sequence. `page`
defaults to 1 and `page_size` to 20, bounded 1 to 100; invalid values receive
422. It SHALL return total and has_next, and no comment text. Responses SHALL
carry `Cache-Control: no-store`.

#### Scenario: Scores tie across pages

- **WHEN** two pending comments have the same score
- **THEN** their insertion order remains stable across page requests

#### Scenario: No pending comments

- **WHEN** the queue is empty
- **THEN** the response contains an empty list, total 0, and has_next false

### Requirement: Existing authentication data survives schema upgrade

Database initialization SHALL migrate schema version 2 to 3, preserving users,
password hashes, sessions and comments. Existing comments SHALL receive simulated
scores so they can appear in the queue. A newer unknown version SHALL be rejected
without overwriting data.

#### Scenario: Upgrade a populated local database

- **WHEN** a version 2 database with users, sessions and comments starts under this API
- **THEN** those records remain and existing comments receive simulated scores

# Spec Delta

## Purpose

Allow authenticated moderators and supervisors to review a shared queue one
comment at a time, preserving human decisions and an attribution trail without
exposing comment text to other viewers or audit logs.

## ADDED Requirements

### Requirement: Queue summaries omit comment text
`GET /comments?status=<status>` SHALL require a valid session and return comment
identifiers, video identifiers, estimated risk, model version and status, never
the comment text. `PENDING` is the default status. Results SHALL be ordered by
decreasing risk and then original input order. A missing or empty queue SHALL
produce an empty array, not a fabricated item.

#### Scenario: Moderator reads an unclaimed queue
- **WHEN** an authenticated moderator requests the pending queue
- **THEN** the API returns summaries in stable risk order without full text

#### Scenario: No item has the requested status
- **WHEN** an authenticated user requests a status with no comments
- **THEN** the API returns HTTP 200 and an empty array

#### Scenario: Anonymous user requests a queue
- **WHEN** a request has no valid session
- **THEN** the API returns HTTP 401 and no comment data

### Requirement: A claim has one current owner
`POST /comments/{id}/claim` SHALL atomically move a `PENDING` comment to
`IN_REVIEW`, create one active assignment to the authenticated user and record
an `assigned` event. The claim SHALL expire after 15 minutes. A competing claim
before expiration, including a repeat by the owner, SHALL return HTTP 409 with
no second active assignment. A missing id SHALL return HTTP 404.

#### Scenario: Two moderators claim concurrently
- **WHEN** two authenticated moderators request the same pending comment at once
- **THEN** one receives a successful claim and the other receives HTTP 409

#### Scenario: Abandoned claim expires
- **WHEN** an assignment has passed its expiry time and the queue is refreshed or the comment is claimed
- **THEN** the expired assignment is closed, an expiry event is recorded and the comment can be claimed again

### Requirement: Full content requires the current claim
`GET /comments/{id}/content` SHALL require the current unexpired assignee and
return the stored text only in the response body. Every successful reveal SHALL
append a `content_revealed` event without copying the text into the audit event.
The response SHALL be marked `Cache-Control: no-store`. Nonowners SHALL get
HTTP 403; missing ids SHALL get HTTP 404.

#### Scenario: Owner reveals content
- **WHEN** the current assignee requests content before lease expiry
- **THEN** the response contains the text and a reveal event is persisted

#### Scenario: Another moderator attempts to reveal content
- **WHEN** a different authenticated user requests that content
- **THEN** the API returns HTTP 403 without the text or a reveal event

### Requirement: Human decisions are append-only and attributed
`POST /comments/{id}/reviews` SHALL require the current unexpired assignee,
one of `NO_ESCALATION`, `ESCALATE_TO_SUPERVISOR`, `INSUFFICIENT_CONTEXT` or
`TRANSFER_REQUESTED`, and a nonblank reason. It SHALL store reviewer id and
display name, comment id, result, reason, decision time and the comment's model
score/version snapshot. It SHALL close the active assignment and append a
`classified` or `escalated` audit event in the same transaction. `NO_ESCALATION`
SHALL result in `CLASSIFIED`; the other three results SHALL result in
`ESCALATED`. Completed comments SHALL leave the pending queue. A second
decision from the old assignment SHALL return HTTP 409 without overwriting it.

#### Scenario: Moderator classifies a comment
- **WHEN** the current assignee submits `NO_ESCALATION` with a reason
- **THEN** the decision is saved, the comment becomes `CLASSIFIED`, it leaves pending and the assignment closes

#### Scenario: Moderator requests further handling
- **WHEN** the current assignee submits an escalation, insufficient-context or transfer result
- **THEN** the decision is saved and the comment becomes `ESCALATED` for later supervisory handling

#### Scenario: Another moderator or stale owner decides
- **WHEN** a nonowner submits a decision while another claim is active
- **THEN** the API returns HTTP 403 and stores no decision
- **WHEN** a closed or expired claim is used to submit a decision
- **THEN** the API returns HTTP 409 and stores no decision

### Requirement: History shows actions without comment text
`GET /comments/{id}/history` SHALL require authentication and return an ordered
event history including actor id/display name and the recorded review result,
reason, score and model version where applicable. Neither the history response
nor `audit_events` SHALL copy the stored comment text field. Review reasons are
human-authored and may themselves contain sensitive details, so history remains
authenticated and non-cacheable. A missing id SHALL return 404.

#### Scenario: Moderator checks a classified item
- **WHEN** a moderator requests history for a classified comment
- **THEN** the claim, reveal and decision events show who acted and when, and the decision metadata is preserved

#### Scenario: Comment text is inspected in the audit store
- **WHEN** the audit rows and normal operational logs are inspected
- **THEN** no full comment text is present

### Requirement: Existing authentication data survives migration
The application SHALL migrate an existing version 1 SQLite authentication
database to the new schema without changing its users or sessions. Startup
against an unsupported newer schema SHALL fail without altering its data.

#### Scenario: Staff session survives startup after migration
- **WHEN** a version 1 database with a valid staff session is initialized by the new backend
- **THEN** the session remains valid and the comment tables are available

#### Scenario: Unknown future version is encountered
- **WHEN** the schema version is newer than supported
- **THEN** initialization fails before altering user or comment data

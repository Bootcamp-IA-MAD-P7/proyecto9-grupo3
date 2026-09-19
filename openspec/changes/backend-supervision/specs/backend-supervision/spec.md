# Spec Delta

## Purpose

Enable staff to handle escalated decisions and reopen closed comments with
supervisor authorization while preserving prior human decisions and audit data.

## ADDED Requirements

### Requirement: Supervisor can resolve escalations
Only a SUPERVISOR SHALL list escalated comments and resolve an ESCALATED
comment with a nonblank reason and an optional local removal recommendation.
Resolution SHALL persist an action, set RESOLVED and append `resolved` audit.
It MUST NOT contact YouTube.

#### Scenario: Supervisor resolves an escalation
- **WHEN** a supervisor resolves an escalated comment
- **THEN** it becomes RESOLVED, leaves escalation listing, and history retains prior review and supervisor action

#### Scenario: Moderator attempts resolution
- **WHEN** a moderator calls a supervisor route
- **THEN** HTTP 403 is returned without a state change

### Requirement: Supervisor can reassign work
Only a SUPERVISOR SHALL reassign an ESCALATED, REOPENED or IN_REVIEW comment
to an active staff user. Reassignment SHALL atomically close any previous
assignment, create one new 15-minute assignment, set IN_REVIEW and append
`reassigned`. The old assignee MUST lose permission to decide. If a supervised claim
expires, ESCALATED or REOPENED SHALL be restored rather than PENDING.

#### Scenario: Reassign a transfer request
- **WHEN** an escalated comment is reassigned to another active moderator
- **THEN** only that moderator owns the new claim and can submit a later review

#### Scenario: Reassign active work
- **WHEN** a supervisor reassigns an IN_REVIEW comment
- **THEN** the previous claim closes and the previous reviewer cannot decide

#### Scenario: Supervised claim expires
- **WHEN** a supervised claim expires before a new review
- **THEN** an escalated or reopened case returns to ESCALATED or REOPENED and remains outside the general queue

### Requirement: Closed comments can request reopening
Authenticated staff SHALL request reopening for CLASSIFIED or RESOLVED comments,
with a nonblank reason and optional note. Request and actor SHALL be persisted.
The comment SHALL enter REOPEN_REQUESTED but remain outside PENDING. At most
one outstanding request (PENDING or NEEDS_INFO) SHALL exist for a comment.

#### Scenario: Moderator requests reopening
- **WHEN** a moderator requests reopening of a classified comment
- **THEN** the request is PENDING and the comment is REOPEN_REQUESTED, without a new claim

#### Scenario: Duplicate request
- **WHEN** a second request is sent while one remains outstanding
- **THEN** HTTP 409 is returned and the existing request remains unchanged

### Requirement: Supervisor controls request outcome
Only a SUPERVISOR SHALL list requests and approve, reject or ask for more
information. Approval of a PENDING request SHALL set REOPENED; it SHALL NOT
place the comment in the general pending queue. A later supervisor reassignment
is required for another review. Rejection SHALL restore the prior closed status.
A request for more information SHALL keep the comment closed; only the original
requester can provide additional information, returning the request to PENDING.
Decisions SHALL record supervisor id, time and reason where applicable.

#### Scenario: Approve and reassign
- **WHEN** a supervisor approves a pending request and reassigns its comment
- **THEN** the comment moves REOPENED then IN_REVIEW and earlier reviews remain intact

#### Scenario: Reject request
- **WHEN** a supervisor rejects a pending request
- **THEN** the previous CLASSIFIED or RESOLVED status is restored and an audit event is appended

#### Scenario: Ask for and provide more information
- **WHEN** the supervisor asks for information and the original requester supplies it
- **THEN** both notes are retained, the request returns to PENDING and the comment remains out of the general queue

### Requirement: Previous decisions remain traceable
Existing reviews SHALL never be overwritten. Each supervisor or reopening
action SHALL append an attributed audit event. Audit rows and normal logs MUST
NOT copy the stored comment text. History SHALL remain authenticated and
uncacheable, and SHALL show reasons and target reviewer where applicable.

#### Scenario: Reopened case is reviewed again
- **WHEN** a newly assigned moderator decides a reopened comment
- **THEN** both reviews and all intervening supervisor events remain in order

### Requirement: Migration preserves existing data
Startup SHALL migrate a version 2 or 3 database to version 4 in one transaction,
preserving users, sessions, comments, assignments, reviews and audit events.
Unknown future schema versions SHALL fail without altering the database.

#### Scenario: Existing review survives migration
- **WHEN** an existing version 2 database starts with this backend
- **THEN** its prior review and audit history remain available alongside new supervisor tables

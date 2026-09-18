# Spec Delta

## ADDED Requirements

### Requirement: Local schema initialization

Startup SHALL initialize a persistent SQLite file at the configured path.
It SHALL create `users` and `comments` in schema version 1 exactly once and
preserve existing records on repeat startup. Unknown newer versions SHALL
be rejected without modifying records.

#### Scenario: Restart with existing records

- **WHEN** a version-1 database containing users and comments is initialized again
- **THEN** both records remain and no duplicate table is created

### Requirement: User and comment integrity

Users SHALL have a unique ID and username, password hash, MODERATOR or
SUPERVISOR role, active flag and creation time. Comments SHALL have a unique
source ID, video ID, text, PENDING default status, increasing insertion
sequence and optional foreign-key assignee to a portal user. The assignee
SHALL represent a reviewer, not an author.

#### Scenario: Invalid relationship or role

- **WHEN** a comment references a nonexistent assignee or a user has an invalid role
- **THEN** SQLite rejects that write

### Requirement: Multi-write atomicity

Connections SHALL commit completed write blocks and roll back all writes in
a block that raises an error.

#### Scenario: Duplicate in a batch

- **WHEN** a second inserted comment repeats an ID in one transaction
- **THEN** neither comment from that transaction persists

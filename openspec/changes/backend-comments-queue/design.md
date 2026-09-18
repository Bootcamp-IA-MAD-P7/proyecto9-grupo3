# Design

## Structure

`router.py` maps HTTP requests and role guards, `schemas.py` validates and narrows
public responses, `service.py` coordinates scoring, `scoring.py` defines a swappable
boundary, and `repository.py` owns SQL. The existing app factory wires them together.

## Storage and ordering

Schema version 2 already has users, sessions and comments. Version 3 adds
scoring metadata to comments and scores existing rows with the simulated adapter.
Each row retains its input identifiers, text, status and monotonic sequence.
The queue orders by `risk_score DESC, sequence ASC`, giving deterministic ties.
Import is one transaction: a duplicate rolls back the whole batch. Scoring
finishes before that transaction, so scoring failure writes nothing. Existing
users, sessions and comments are preserved.

## Simulated scoring

The adapter hashes text to a stable number in [0, 1]. This is arbitrary demo
ordering, not a toxicity estimate. Responses carry `score_source=SIMULATED`,
`model_version=simulated-v1`, and `uncertainty=1.0`. A real model can later
implement the same `score_comment` boundary only after evaluation and approval.

## Privacy and failure behavior

Only a supervisor imports. Both roles read the queue. Queue SQL never selects
text and the output schema has no text field. Responses are non-cacheable.
Validation errors do not echo submitted content. Invalid input yields 422,
existing IDs 409, scoring failure 503, missing sessions 401 and wrong role 403.
No text reveal endpoint is introduced. The local database stays under ignored
`data/local/` by default. Application code does not log comment bodies.

## Trade-offs and rollback

Offset pagination is simple to teach and sufficient for an initial local queue;
new imports between page requests can shift entries. Cursor pagination can replace
it when concurrent ingestion is needed. SQLite version 3 cannot be rolled back
by running old code against the same file; preserve a copy of the database before
migration if rollback is needed. Raw input is retained locally for later review,
so production deployment needs a retention policy and access controls.

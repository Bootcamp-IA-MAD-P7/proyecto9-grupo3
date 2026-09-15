## Context

See proposal.md for motivation and specs/dataset-extraction/spec.md
for requirements. Extraction and six automated tests are implemented.

## Goals / Non-Goals

Goals: reusable CSV loading with explicit validation.
Non-goals: preprocessing, splitting, training or external actions.

## Decisions

- Use a Python module rather than notebook-only logic so tests,
  future notebooks and training can reuse the same function.
- Use pandas, recorded in requirements.txt, rather than manual
  CSV parsing to minimize implementation time.
- Receive the path through DATASET_PATH for CLI execution;
  extract_dataset accepts a path directly for reuse and testing.
- Stop on invalid inputs rather than silently fixing or dropping
  rows. Accept binary targets represented as 0/1 or booleans.
- Use synthetic temporary CSVs in pytest rather than real comments.
  Record pytest in requirements-dev.txt.
- Print only schema metadata, row counts and target distribution.

## Risks / Trade-offs

- Limited validation does not detect contextual leakage or conflicting
  labels → investigate these during EDA.
- Real comments may contain sensitive content → exclude them from
  logs, errors and test fixtures.
- CSV redistribution remains unresolved → reconcile the requested
  repository upload with the proposal and harness before PR approval.

## Migration Plan

Install recorded dependencies, configure DATASET_PATH and run extraction
and tests. No persistent data changes occur. Rollback by reverting the
change through a reviewed PR.
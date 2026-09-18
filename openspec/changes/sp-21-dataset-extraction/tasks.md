## 1. Extraction

- [x] 1.1 Implement configurable CSV loading; verified locally by extraction of 1000 rows and 15 columns.
- [x] 1.2 Validate missing files, required columns, empty data, blank text and binary targets; six tests passed in Fernanda's local execution.
- [x] 1.3 Record pandas and pytest versions; verified in requirements.txt and requirements-dev.txt.
- [x] 1.4 Verify row order, missing text and metadata-only output with three additional automated tests; 9 tests passed on 2026-09-15 (132.36 seconds).

## 2. Delivery

- [ ] 2.1 Reconcile the decision to version the CSV in dev but exclude it from main with SDD and harness; record redistribution status and promotion procedure for review.
- [x] 2.2 Validate OpenSpec strictly and run git diff --check; both commands passed on 2026-09-15.
- [ ] 2.3 Open a PR into dev with Jira, test evidence and rollback; obtain another teammate's approval.

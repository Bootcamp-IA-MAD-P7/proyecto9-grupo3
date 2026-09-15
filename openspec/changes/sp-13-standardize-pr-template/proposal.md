## Why

SP-13 gives the team one professional, evidence-first PR structure while
avoiding unnecessary OpenSpec changes for non-material work. The existing
template is useful but does not distinguish material specifications from a
reviewable non-material justification.

## What Changes

- Replace the initial PR template with a standard English structure for
  traceability, outcome, acceptance criteria, validation, safety, rollback, and
  review.
- Require explicit Jira and OpenSpec fields through the existing harness.
- Permit `N/A — <reason>` only as a reviewable declaration for non-material
  changes.
- Add standard-library tests for the metadata rule.

### Validated facts

- Jira story: SP-13.
- The repository has one existing PR template and one dependency-light
  validation workflow.
- SP-57 already validates Conventional Commit PR titles.

### Non-goals

- Adding issue templates, dependencies, workflows, GitHub Settings, or automatic
  materiality classification.
- Replacing Jira, OpenSpec, or independent review with template text.

## Impact

Future PRs present consistent evidence to reviewers. A missing Jira field or
unexplained absent OpenSpec field fails the existing `validate` check.

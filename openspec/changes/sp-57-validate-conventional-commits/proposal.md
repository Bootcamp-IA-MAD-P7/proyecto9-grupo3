## Why

SP-57 turns the team's agreed Conventional Commit convention into a small,
automatic PR gate without adding a new dependency or workflow. With squash
merge, a compliant PR title provides reviewable evidence for the commit that
enters the integration history.

## What Changes

- Validate PR titles with the existing dependency-light harness.
- Allow only `feat`, `fix`, `docs`, `test`, `ci`, and `chore` types, optionally
  with a lowercase scope, followed by a lowercase description.
- Add standard-library tests for accepted and rejected PR payloads.
- Record the squash-merge rationale in the canonical standards.

### Validated facts

- Jira story: SP-57.
- The existing `validate` workflow runs `scripts/validate_harness.py` for pull
  requests into `dev` and `main`.
- `dev` integrates focused changes through squash merge.

### Non-goals

- Adding commitlint, Node, dependencies, workflows, GitHub settings, or title
  rewriting.
- Inferring whether prose is genuinely English.
- Validating or rewriting intermediate commits on a PR branch.

## Impact

PRs with an invalid title fail the existing required `validate` check. Existing
Jira, branch naming, OpenSpec, and release-source validation remain unchanged.

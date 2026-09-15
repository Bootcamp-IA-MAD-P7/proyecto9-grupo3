## Why

SP-58 records the already configured squash-only merge strategy as canonical
team policy. This keeps focused Jira changes traceable in a linear history
without adding tooling or changing the approved review, check, or release flow.

## What Changes

- Document squash merge as the only integration strategy for PRs into `dev` and
  `main`.
- Record that GitHub allows squash merge and disables merge commits and rebase
  merge.
- Preserve the relationship between the Conventional Commit PR title and the
  final integrated commit.

## Non-goals

- Changing GitHub Settings, branch protection, workflows, checks, approvals,
  release automation, tags, or application code.

## Evidence

Read-only GitHub CLI inspection confirms squash merge is enabled, merge commit
and rebase merge are disabled, and `dev` and `main` require linear history.

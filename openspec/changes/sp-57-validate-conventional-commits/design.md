## Context

The team already documents Conventional Commits but the harness does not enforce
them. GitHub Actions receives PR metadata, while inspecting every intermediate
commit would add complexity without improving the final squash-merged history.

## Decision

The existing Python validator checks `pull_request.title` only when invoked for
a pull-request event. It uses a regular expression equivalent to:

`^(feat|fix|docs|test|ci|chore)(\([a-z0-9][a-z0-9-]*\))?!?: [a-z0-9].+$`

This accepts the allowed types, an optional lowercase scope and optional
breaking-change marker, a colon, and a description beginning in lowercase. It
does not attempt to classify natural-language quality or the actual language of
the description.

The same rule applies to a release PR from `dev` to `main`; existing checks for
source branch and source repository continue to apply independently.

## Alternatives considered

- **Commitlint or a new workflow:** rejected because it adds a toolchain and
  maintenance cost disproportionate to the project window.
- **Inspect all commits in the PR:** rejected because the team uses squash merge
  and the PR title is the reviewable representation of the integrated commit.
- **Validate English automatically:** rejected because a regex cannot make that
  claim reliably; reviewers retain that judgment.

## Verification and rollback

`unittest` payload tests cover valid titles, invalid structure, and a valid
release PR. The existing harness runs unchanged in CI. If the policy proves too
restrictive, revert this focused change; no data, deployment, or external state
is affected.

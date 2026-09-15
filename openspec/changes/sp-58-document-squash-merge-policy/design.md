## Decision

The repository uses squash merge exclusively for PRs integrated into `dev` and
`main`. The GitHub repository setting enables squash merge and disables merge
commit and rebase merge. Branch protection additionally requires linear history
on both integration branches.

This fits a short project because one focused Jira PR becomes one reviewable
commit, represented by its validated Conventional Commit title. It avoids merge
commit noise and rebase-based history rewriting without introducing another
tool, workflow, or release process.

## Boundaries

SP-58 documents existing configuration only. It does not change approval count,
required checks, release promotion, tags, GitHub Settings, or runtime behavior.

## Verification and rollback

Use read-only GitHub CLI inspection for repository merge settings and branch
protection, plus harness validation and `git diff --check`. If the policy is
revised, update the GitHub setting and this standard together through a new
traceable change.

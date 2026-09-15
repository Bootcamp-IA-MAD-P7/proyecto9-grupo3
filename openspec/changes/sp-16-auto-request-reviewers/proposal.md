## Why

SP-16 already requires an independent approval before merge. Adding repository
code owners ensures that Miguel, Gabriela, and Fernanda receive a review request
by default, reducing the chance that a focused PR waits for an unassigned reviewer.

## What Changes

- Add one repository-wide CODEOWNERS rule for `@miguelRedondoWeb`, `@fer-trk`,
  and `@gabrielagranja`.
- Preserve the existing single independent-approval rule; both people are
  requested, but one approval remains sufficient.

## Non-goals

- Changing branch protection, approval count, CODEOWNERS enforcement, workflows,
  teams, or GitHub Settings.
- Assigning an individual owner to product, data, model, or architecture files.

## Impact

GitHub requests review from the three named contributors for PRs that modify any
repository file after this change is merged.

## Context

The team has few working days and already uses a dependency-light harness. The
current PR template has traceability and evidence sections, but it always
implies an OpenSpec path even for documentation-only work. The standards require
OpenSpec for material changes, not for every edit.

## Decision

Use one English PR template with a stable section order: context and
traceability, outcome, acceptance criteria, validation, data/security/operations,
risks/rollback, and review. The Jira and OpenSpec fields are required by the
existing Python validator.

The OpenSpec value is valid when it matches
`openspec/changes/<lowercase-kebab-case-change>/`, optionally wrapped in
backticks, and that directory exists in the repository. It may instead be
`N/A — <non-empty reason>`. The validator checks path structure and local
existence, but cannot determine whether a change is genuinely non-material; the
author must state the reason and the independent reviewer must assess it.

## Alternatives considered

- **Require OpenSpec on every PR:** rejected because it creates redundant specs
  for typo-only and documentation-only changes.
- **Infer materiality automatically:** rejected because a lightweight harness
  cannot reliably interpret product or technical scope.
- **Add a PR metadata tool or workflow:** rejected because the existing Python
  harness and required `validate` check already provide the needed gate.

## Verification and rollback

Standard-library unit tests cover material and non-material declarations plus
missing fields. The existing harness continues to run in CI. Reverting this
focused change restores the previous template and validation behavior; no
product, data, deployment, or external state is affected.

---
name: adversarial-review
description: Independently test whether a change actually satisfies its Jira and OpenSpec contract. Use before archive, merge, deployment, or when the team requests a critical spec-to-evidence review.
---

# Adversarial review

Try to falsify completion. The author demonstrating a happy path is not sufficient
evidence.

## Inputs

Read:

- `docs/base-standards.md`.
- The Jira story and approved acceptance criteria.
- The complete OpenSpec proposal, requirements, scenarios, design, and tasks.
- The full branch diff or PR, tests, and verification evidence.

If a required input is unavailable, state what is missing and do not issue a pass.

## Review

1. Map every acceptance criterion and scenario to implementation and evidence.
2. Look for spec drift, hidden scope, untested errors, boundary inputs, state
   recovery, security, privacy, accessibility, and operational failure.
3. For data and ML changes, challenge provenance, leakage, imbalance,
   reproducibility, class meaning, thresholds, subgroup behavior, and unsupported
   performance claims.
4. For moderation, challenge any inference that sentiment proves harmfulness.
   Verify explicit abstention when context is insufficient.
5. For Jira, GitHub, AWS, or YouTube writes, verify exact authorization, least
   privilege, dry-run or test-environment evidence, confirmation, and rollback.
6. Distinguish a missing implementation from a missing or incorrect spec; propose
   the correction in the proper artifact.

## Output

Provide:

- Scope and sources reviewed.
- Criterion-to-evidence mapping.
- Findings classified as `BLOCKER`, `MAJOR`, `MINOR`, or `QUESTION`.
- The artifact that must change: Jira, OpenSpec, code, tests, docs, or operations.
- Verdict: `PASS`, `PASS WITH GAPS`, or `FAIL`.
- Whether archive, merge, or deployment is advisable now.

Any blocker or major finding produces `FAIL`. Do not dilute findings with generic
praise. Never fix, merge, deploy, archive, or write to external systems unless the
user separately authorizes that action.


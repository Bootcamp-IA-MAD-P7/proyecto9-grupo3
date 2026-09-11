---
name: enrich-jira-story
description: Refine a Jira SP user story collaboratively before OpenSpec planning. Use when a story is vague, proposed criteria need team discussion, or the user asks to prepare or update a Jira story. Do not use for implementation or silent Jira write-back.
---

# Enrich Jira story

Turn a Jira story into a team-reviewable product contract without treating AI
suggestions as decisions.

## Read first

1. Read `docs/base-standards.md`.
2. Read the requested Jira issue and its latest version when a key is provided.
3. Read only the product, data, UX, or architecture context relevant to the story.

## Review mode (default)

Preserve the original story and produce:

1. **Current understanding** — user, need, outcome, and current scope.
2. **Validated facts** — only facts supported by Jira or team-approved context.
3. **Assumptions** — plausible but unapproved statements.
4. **Questions for the team** — decisions that materially change scope or risk.
5. **Proposed refinement** — concise story, acceptance criteria, non-goals,
   dependencies, risks, evidence, and learning question.
6. **Readiness verdict** — `READY FOR TEAM REVIEW`, `READY FOR OPENSPEC`, or
   `NOT READY`, with the missing conditions.

Acceptance criteria must be observable and must not prescribe an implementation
unless the implementation itself is an approved constraint.

For ML or moderation work, explicitly examine:

- Dataset provenance, labels, leakage, language, and evaluation evidence.
- The distinction between sentiment, toxicity, and policy violation.
- Low-confidence, insufficient-context, and abstention behavior.
- Human control over recommendations and external actions.
- UX empty, loading, error, recovery, and explanation states.

Never invent answers to open questions. A suggested threshold, service, model, or
architecture remains an assumption until the team validates it.

## Jira write-back mode

Writing is allowed only after the user explicitly approves the exact proposed
refinement and asks to update a named Jira key.

Immediately before writing:

1. Fetch the issue again.
2. If it changed since review, stop and show the conflict.
3. Preserve existing content unless replacement was explicitly requested.
4. Change only the approved description or criteria. Do not change status,
   assignee, points, labels, sprint, or hierarchy without separate authorization.
5. Return a concise summary of exactly what changed.

Do not create additional stories, subtasks, or dependencies implicitly.


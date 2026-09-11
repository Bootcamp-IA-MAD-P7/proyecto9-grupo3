# Base standards

This document is the authoritative project harness for Gabriela, Miguel, Fernanda,
and coding agents working in this repository.

## 1. Mission and team model

Build an evidence-backed tool that helps YouTube moderators prioritize comments
for human review. Gabriela, Miguel, and Fernanda have equal development standing.
Each contributor maintains a primary focus during the project. Review, pairing,
and cross-functional participation rotate by story. A Jira owner coordinates a
story; neither focus nor ownership grants unilateral product or technical
authority.

Every contributor must be able to explain the product, data, model, architecture,
quality evidence, and deployment at an appropriate level.

## 2. Sources of truth

- Jira owns priority, responsibility, workflow state, and approved product-level
  acceptance criteria.
- OpenSpec owns the versioned behavioral contract, scenarios, technical design,
  and implementation tasks.
- Git owns implementation, tests, standards, decisions, and evidence.
- If the product is deployed to AWS, its behavior is operational evidence, never
  a substitute for the spec. The AWS architecture has not been selected yet.

When artifacts disagree, stop and reconcile them. Do not silently choose one.

## 3. Required delivery flow

1. Select one Jira work item and confirm its `SP-<number>` key.
2. Enrich unclear stories collaboratively; separate questions from proposals.
3. Obtain team agreement on scope, non-goals, acceptance criteria, and UX impact.
4. Create or update `openspec/changes/<jira-key>-<slug>/` for material changes.
5. Work on `<type>/<JIRA-KEY>-<short-description>` from an up-to-date `main`.
6. Implement the smallest useful slice with tests and reviewable evidence.
7. Verify every acceptance scenario and perform an independent review.
8. Open a PR linking Jira, OpenSpec, tests, evidence, risks, and rollback.
9. Merge only with required checks green and approval from another teammate.
10. Deploy only when authorized; verify the deployed behavior and update Jira.

Allowed branch types are `feature`, `fix`, `docs`, `test`, `ci`, and `chore`.
Use Conventional Commits in English. Prefer squash merge for a focused Jira item.

## 4. When OpenSpec is required

An OpenSpec change is required for:

- User-visible behavior or UX flows.
- Data ingestion, preprocessing, labeling, splitting, or schema changes.
- Model selection, training, evaluation, thresholds, or output contracts.
- APIs, persistent data, security, privacy, or external integrations.
- Deployment architecture or behavior.
- Harness rules that change how contributors or agents work.

It is normally unnecessary for typo-only documentation fixes, formatting, or a
mechanical dependency refresh with no behavioral impact. If uncertain, write a
small spec rather than hiding the decision in chat.

## 5. Definition of Ready

A story is ready only when it has:

- A user or stakeholder and a real need.
- An observable outcome and measurable acceptance criteria.
- Explicit scope and non-goals.
- Known dependencies, risks, and learning question.
- A responsible contributor and a different reviewer.
- Team agreement, recorded in Jira or the linked spec.

## 6. Definition of Done

- The implementation matches the accepted Jira story and OpenSpec scenarios.
- Each acceptance criterion has automated or inspectable evidence.
- Relevant happy, empty, loading, error, recovery, and boundary states are tested.
- Data leakage, bias, privacy, security, accessibility, and observability impacts
  were considered where relevant.
- Documentation and Jira state match reality.
- A teammate other than the author reviewed the work.
- Deployed changes include an appropriate smoke test and rollback note.

## 7. Product and ML safety

- Sentiment, toxicity, policy violation, and harmful-content risk are different
  concepts. Never present one as proof of another.
- Predictions expose model version, label, and interpretable confidence or
  uncertainty information.
- Product hypothesis: when evidence or conversational context is insufficient,
  an abstention response that recommends human review may reduce unsupported
  conclusions. This behavior must be validated before becoming a requirement.
- Product hypothesis: English may be the initial language because it matches the
  currently available dataset. Language scope remains a team decision; Spanish
  requires appropriate data and evaluation.
- Dataset licenses, provenance, class definitions, missingness, duplicates,
  leakage, imbalance, and subgroup behavior must be documented before claims.
- Thresholds must be justified with validation evidence and the cost of errors;
  never select them only because they look plausible.

## 8. External-action safety

- Default to reports, previews, or dry runs for YouTube, Jira, GitHub, and AWS.
- Reading an external system does not authorize writing to it.
- Irreversible, user-affecting, deployment, merge, moderation, or access-control
  actions require explicit authorization at the time of action.
- YouTube moderation experiments use a test channel and test content first.
- Never reject content or ban an author automatically. An authorized human must
  review the evidence and confirm the exact action.
- Never commit credentials, tokens, personal data, raw sensitive text, or `.env`.

## 9. Verification and review

Testing depth follows risk rather than a universal coverage number. Start with a
failing behavioral test when practical; always test meaningful error and boundary
conditions. Model changes require reproducible evaluation and error analysis.

The author demonstrates compliance; an independent reviewer tries to falsify it.
Blockers include spec violations, unsupported model claims, data leakage, privacy
or security risks, missing acceptance evidence, and unauthorized external action.

## 10. Language and learning

- Code identifiers, APIs, configuration keys, branches, commits, and test names
  use English.
- Jira discussion and learning-oriented documents may use Spanish so the team can
  reason precisely.
- Public technical documentation may be bilingual; the team will revisit this
  convention before presentation.
- Record why a decision was made, alternatives considered, and what evidence could
  change it.

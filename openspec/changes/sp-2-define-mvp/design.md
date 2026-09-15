## Context

See `proposal.md` for the product motivation and
`specs/moderation-mvp-definition/spec.md` for the behavioral contract. SP-2 is a
definition change that constrains later data, model, interface, and queue work.
The team has seven working days, one small historical dataset, and no selected
AWS architecture.

The supplied CSV contains 1,000 complete rows grouped into 13 videos. Its
hierarchical labels describe toxicity and several harmful-content categories;
they do not provide positive, neutral, and negative sentiment. Several child
labels are too sparse to support credible standalone MVP classifiers.

## Goals / Non-Goals

**Goals:**

- Give downstream stories one small, testable target and primary journey.
- Preserve traceability from Jira through OpenSpec to future evidence.
- Prevent leakage, overclaiming, sensitive-text logging, and automatic actions.
- Keep the contract compatible with an early AWS deployment without selecting
  infrastructure prematurely.

**Non-Goals:**

- Choose libraries, model family, API shape, frontend framework, or AWS service.
- Fix a probability threshold before baseline and error-cost evidence exists.
- Design direct YouTube moderation or a production feedback-learning pipeline.

## Decisions

### Use `IsToxic` as the single MVP prediction target

The binary parent label has 462 positive and 538 negative examples, making it
the most defensible target for a first vertical slice. Product copy will call it
"toxicidad" or "riesgo de toxicidad", never sentiment or policy enforcement.

Alternatives considered:

- Three-way sentiment was rejected because the dataset has no sentiment labels.
- Multilabel subclasses were deferred because some have 0, 1, 8, 12, or 21
  positives; a polished output would overstate the available evidence.

### Rank the queue by estimated `P(IsToxic)`

The primary output contract is a descending score used for prioritization. A
deterministic source order will resolve equal scores so reruns remain reviewable.
The score is an estimate, not a severity scale. Threshold-based abstention stays
a hypothesis until model evidence and moderator error costs are known.

An unranked dataset browser was considered but does not test the central value
hypothesis: helping a moderator choose what to inspect first.

### Treat manual input as a secondary route

A pasted-comment route is useful for demos and exploratory checks, but it must
reuse the same output language and must not displace the queue. Direct YouTube
ingestion is deferred because OAuth, permissions, quota, and user-impact safety
would consume the short delivery window.

### Keep the review mark local and reversible

The MVP records only whether a queue item has been reviewed and allows that mark
to be undone. It does not encode a YouTube action or change the model output.
The persistence mechanism remains an implementation choice as long as the state
does not leave the product or imply external moderation.

### Keep source data local until usage rights are confirmed

The repository may contain aggregate, non-text dataset evidence but not the raw
CSV until its redistribution terms are confirmed. Runtime paths and secrets must
be configurable and ignored by Git. Raw comments must not appear in logs,
screenshots, or analytics evidence.

### Group evaluation partitions by `VideoId`

Downstream model work should keep comments from the same video in one partition
to reduce contextual leakage. With only 13 groups, the team must report the
resulting variance and class balance. A random row split is simpler but risks an
optimistic estimate from shared video context.

### Separate product layers and preserve observability

Later implementation should separate dataset loading, prediction, ranking, and
presentation so each can fail visibly and be tested independently. Reviewable
predictions should include target name, score, model version, and a trace-safe
record identifier; they must exclude raw text from operational logs.

### Use a Spec Kit-inspired planning sequence

The repository maps shared principles to `docs/base-standards.md`, product intent
to Jira and `proposal.md`, observable behavior to delta specs, technical choices
to `design.md`, and verifiable work to `tasks.md`. This borrows Spec Kit's
separation of concerns without adopting an additional parallel framework.

## Risks / Trade-offs

- [Historical and topic-specific data] -> State the 2014 Ferguson scope on the
  dataset card and avoid claims about all present-day YouTube comments.
- [Only 13 videos] -> Use grouped evaluation and report instability rather than
  hiding it behind a single metric.
- [Toxicity mistaken for sentiment or intent] -> Enforce exact product language
  in acceptance scenarios, UI review, and error analysis.
- [Probability mistaken for severity] -> Explain the score near the result and
  test comprehension with users.
- [Classifiers for sparse subclasses look impressive but unreliable] -> Defer
  them until adequate data and per-class evidence exist.
- [License remains unresolved] -> Do not commit or redistribute the raw CSV.
- [AWS work starts before behavior is stable] -> Deploy the smallest accepted
  vertical slice; record architecture separately when requirements are known.

## Migration Plan

This change modifies planning artifacts only. After team approval, downstream
stories SP-20, SP-34, SP-50, and SP-54 should reference this contract before
implementation. If the team rejects a product decision, revise the Jira story
and this change together; no runtime rollback is required.

## Open Questions

- Which people will participate in the rapid UX test, and what baseline will
  make a completion-time target meaningful?
- Does the dataset's source record permit redistribution of the CSV?
- What queue size gives a useful demo without creating unnecessary UI work?

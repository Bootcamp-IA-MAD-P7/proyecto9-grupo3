## Why

SP-2 must turn the team's early moderation idea into an evidence-backed MVP
decision before model, interface, queue, or AWS work fixes the wrong behavior.
The agreed outcome is a human-controlled queue that helps a YouTube moderator
decide which dataset comment to review first.

## What Changes

- Define the primary MVP journey as a dataset-backed review queue ordered by the
  model's estimated probability of `IsToxic`.
- Define pasted-comment analysis as a secondary journey.
- Use toxicity language and explicitly distinguish it from sentiment, hate
  speech, harmful-content risk, and platform policy violations.
- Capture measurable product, UX, model, safety, and learning outcomes without
  presenting unvalidated targets as facts.
- Document the supplied dataset's verified structure and limitations so later
  stories cannot silently overstate model capability.
- Keep final moderation decisions under human control.

### Validated facts

- Jira story: SP-2, under epic SP-1.
- The team selected a prioritized dataset queue as the primary MVP journey.
- `youtoxic_english_1000.csv` contains 1,000 complete rows across 13 videos;
  `IsToxic` has 462 positive and 538 negative labels.
- Several subclasses have between zero and 21 positive examples, and the source
  is limited to English comments about the Ferguson unrest in 2014.

### Assumptions to validate

- Ranking by estimated `IsToxic` probability improves a moderator's first-review
  decision compared with an unranked list.
- English may be the initial product language because it matches the dataset.
- Showing probability can be made understandable without implying certainty or
  severity.

### Open questions

- Which secondary persona, if any, matters for the MVP?
- What UX success target and test population are credible within seven days?
- What model threshold or queue size supports the moderation task?
- Does the dataset license permit repository redistribution?

### Non-goals

- Sentiment classification, reliable subclass classifiers, or Spanish support.
- Direct YouTube ingestion, deletion, rejection, or author banning.
- Claims that results generalize to all current YouTube comments.
- Selecting AWS architecture in this product-definition change.

## Capabilities

### New Capabilities

- `moderation-mvp-definition`: Defines the agreed moderation journeys, product
  boundaries, measurable outcomes, and evidence required before implementation.

### Modified Capabilities

None.

## Impact

- Product documentation will gain an evidence-backed MVP definition and dataset
  card.
- SP-20, SP-34, SP-50, and SP-54 must align their model, interface, queue, and
  batch-processing behavior with this contract.
- No production code, API, model, AWS infrastructure, or YouTube state changes
  are part of SP-2.

# Design · SP-10 project harness

## Source-of-truth boundaries

| Artifact | Owns |
|---|---|
| Jira | priority, ownership, workflow state, product acceptance criteria |
| OpenSpec | agreed behavioral contract, scenarios, design, implementation tasks |
| Git | code, tests, standards, evidence, decision history |
| AWS | future runtime evidence; architecture not yet selected |

`docs/base-standards.md` is the canonical repository standard. `AGENTS.md` is a
short discovery entrypoint so rules are not duplicated across agent files.

## Delivery loop

1. Read and collaboratively enrich the Jira story.
2. Obtain human acceptance of scope and criteria.
3. Create or update the OpenSpec change.
4. Implement small tasks with tests and evidence.
5. Verify each scenario and run an independent adversarial review.
6. Open a PR linked to Jira and the OpenSpec change.
7. Merge only after a teammate approves and required checks pass.
8. Deploy when authorized, record evidence, and update Jira to reflect reality.

## Product-safety rules

- Sentiment and harmful-content risk are separate signals.
- Abstaining and recommending human review when context is insufficient is a
  product hypothesis to validate, not mandatory MVP behavior.
- English as the initial language is a dataset-based hypothesis, not an accepted
  product requirement.
- Irreversible or external platform actions always require explicit human
  confirmation and appropriate authorization.
- A future YouTube integration starts in a test channel and remains optional for
  the MVP.

## Adaptation from LIDR Specboot

Adopt the single-source standards pattern, reusable skills, OpenSpec artifacts,
incremental work, and adversarial verification. Adapt language, testing, and
technology rules to a Python NLP product. Do not adopt Claude-specific model
settings, fixed TypeScript rules, mandatory database steps, or a universal
coverage percentage without project evidence.

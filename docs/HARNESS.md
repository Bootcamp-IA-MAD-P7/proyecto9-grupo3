# Project harness

## Purpose

The harness is the set of repository instructions, specifications, skills, gates,
and evidence that makes AI-assisted work predictable and reviewable. It does not
replace team judgment.

## Components

| Component | Location | Purpose |
|---|---|---|
| Agent entrypoint | `AGENTS.md` | Direct every agent to the same standards |
| Canonical standards | `docs/base-standards.md` | Team, product, safety, and delivery rules |
| Product context | `docs/product/` | Current hypotheses and discovery evidence |
| OpenSpec config | `openspec/config.yaml` | Context and artifact rules |
| OpenSpec changes | `openspec/changes/` | Proposal, behavior, design, and tasks |
| Reusable skills | `.agents/skills/` | Repeatable Jira and review workflows |
| PR template | `.github/pull_request_template.md` | Traceability and evidence at review time |
| Automated gate | `scripts/validate_harness.py` | Fast structural feedback locally and in CI |

## Lifecycle

`Jira -> collaborative enrichment -> team approval -> OpenSpec -> branch -> tests
-> adversarial review -> PR -> teammate approval -> deploy -> evidence -> Jira`

### Human gates

- **Story gate:** the team accepts the problem and product criteria.
- **Spec gate:** the team accepts behavior, non-goals, and risks before code.
- **Review gate:** someone other than the author reviews evidence and assumptions.
- **External-action gate:** an authorized human confirms the exact write, deploy,
  moderation, or access-control action.

## LIDR Specboot adaptation

Reference: <https://github.com/LIDR-academy/lidr-specboot>

### Adopted

- One canonical standards document.
- OpenSpec as the versioned specification layer.
- Small, traceable changes and reusable agent skills.
- Story enrichment before implementation.
- Verification plus adversarial review.

### Adapted

- The default standards are tailored to a Python NLP moderation product.
- Testing is risk-based; no arbitrary global coverage percentage is imposed.
- Product and learning documents can remain in Spanish.
- Skills require human approval before writing to Jira or external systems.
- Windows-compatible real files are used instead of depending on symlinks.

### Deferred

- Stack-specific backend and frontend standards until architecture is selected.
- Database and API contracts until the vertical slice requires them.
- Worktrees until the team decides whether their added isolation is worth the
  learning overhead during this seven-day project.

### Rejected

- Claude-specific model configuration.
- TypeScript-only rules.
- Mandatory database and curl steps for changes where they do not apply.
- Automatic external mutations or silent Jira enrichment.

## Everyday commands

OpenSpec generates Codex skills under `.agents/skills/`. The core flow is:

1. `$openspec-explore` for uncertain product or technical questions.
2. `$enrich-jira-story SP-<number>` to prepare a collaborative refinement.
3. `$openspec-propose` after the team accepts the story.
4. `$openspec-apply-change` to implement accepted tasks.
5. `$openspec-update-change` if learning changes the design during implementation.
6. `$adversarial-review` before archive and PR approval.
7. `$openspec-archive-change` only after verification and review.

The exact OpenSpec invocation may vary by Codex version; generated skills are the
authoritative interface.

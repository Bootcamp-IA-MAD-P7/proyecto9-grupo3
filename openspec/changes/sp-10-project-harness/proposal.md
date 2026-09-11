# SP-10 · Project harness

## Why

The team has seven working days, three equally responsible contributors, and a
requirement to connect Jira, specifications, implementation, review, and AWS
evidence. A repository-level harness is needed to keep those links explicit and
to prevent AI-assisted work from silently changing agreed product scope.

## What changes

- Establish one authoritative set of project standards.
- Define the Jira-to-OpenSpec-to-PR delivery workflow.
- Add a collaborative Jira story enrichment skill.
- Add an independent adversarial review skill.
- Add pull-request and automated structural quality gates.
- Encode human control of external actions and distinguish accepted rules from
  unvalidated product hypotheses.

## Non-goals

- Choosing the final application architecture or ML model.
- Selecting the AWS architecture, initial product language, or final uncertainty
  behavior before product and data validation.
- Enforcing stack-specific lint, typing, or coverage before the stack is chosen.
- Automatically changing Jira stories, merging pull requests, deploying to AWS,
  or performing actions on YouTube without explicit human authorization.
- Copying every rule from LIDR Specboot unchanged.

## Jira traceability

- Story: SP-10
- Epic: SP-1
- Owner in Jira: Miguel Redondo
- Working branch: `feature/SP-10-project-harness`

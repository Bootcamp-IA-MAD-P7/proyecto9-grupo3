## ADDED Requirements

### Requirement: Shared reviewers are requested automatically

The repository SHALL define `@miguelRedondoWeb`, `@fer-trk`, and
`@gabrielagranja` as code owners for all repository paths. GitHub SHALL request
their review when a PR changes a matching path.

#### Scenario: A contributor opens a focused PR

- **WHEN** a PR changes a repository file
- **THEN** GitHub requests review from `@miguelRedondoWeb`, `@fer-trk`, and
  `@gabrielagranja`

### Requirement: Automatic requests do not increase approval count

The CODEOWNERS rule SHALL NOT change the existing requirement for one independent
approval before merge.

#### Scenario: One requested reviewer approves

- **WHEN** one of the automatically requested reviewers submits an approval
- **THEN** the review-count requirement is satisfied if all other required gates
  are also green

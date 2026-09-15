## Decision

Use the smallest possible CODEOWNERS rule:

`* @miguelRedondoWeb @fer-trk @gabrielagranja`

The wildcard covers every repository path, matching the three-person team's
shared responsibility model. It requests all three contributors automatically
while the existing branch protection still requires one independent approval
before merge.

## Alternatives considered

- **Manual reviewer selection on every PR:** rejected because it is easy to
  forget and adds repeated coordination work.
- **Directory-specific owners:** deferred until the application architecture and
  ownership boundaries exist.
- **Require Code Owner reviews:** not enabled because the current single-review
  rule already meets the agreed policy and requiring both approvals would add
  friction during the short project.

## Verification and rollback

Verify the file contains the exact GitHub handles and has one wildcard rule.
After merge, open a small PR and confirm GitHub requests all three reviewers. Revert
the CODEOWNERS commit to remove automatic requests; branch-protection review
requirements remain unchanged.

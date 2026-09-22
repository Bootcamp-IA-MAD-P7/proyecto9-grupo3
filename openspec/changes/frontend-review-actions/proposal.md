# Proposal: Human review actions in the moderation frontend

## Problem and outcome

The moderation queue currently exposes prioritisation signals but not the authorised comment text or a persistent way for a moderator to record a human decision. This vertical connects the selected queue item to the protected detail endpoint and records the review decision through the FastAPI API.

Primary user: the human moderator who needs enough authorised context to review a case and leave an auditable decision.

Expected outcome: a moderator can select a queue item, inspect its full text only in the authorised detail view, choose a supported review action, optionally add a non-sensitive note, and receive durable feedback from the backend.

Traceability: Jira key not supplied in the request; assign the project key before formal PR tracking. This proposal is otherwise scoped to `feat/frontend-review-actions`.

## Relationship to previous verticals

This builds on the merged authentication and real queue vertical. It reuses the in-memory bearer token, central API client, authenticated queue, existing status model, and the separation between model signals and human decisions.

## Included scope

- OpenSpec artifacts for the vertical.
- `GET /comments/{comment_id}` integration.
- `POST /comments/{comment_id}/review` integration.
- Detail rendering for text, risk, uncertainty, source, model version, video and status.
- `NEEDS_REVIEW`, `CONFIRMED_TOXIC` and `NOT_TOXIC` controls.
- Confirmation for final decisions, optional notes, validation, conflict/error feedback and accessible focus/live-region behaviour.
- Responsive semantic UI and documentation of validation limitations.

## Excluded scope

- Automatic deletion, blocking, sanctions, reports or publishing.
- New model categories, model scoring, policy enforcement, external services or comment exports.
- Token persistence, backend changes, database migrations, real comments, deployment or merge.

## Ethical, privacy and security risks

- Model risk and uncertainty must remain visible as prioritisation signals, never as verdicts.
- Comment text is sensitive and is rendered only after the authorised detail response; it is not logged, persisted by the frontend or sent to external services.
- Notes must not contain credentials or sensitive data and are bounded in length.
- The browser keeps access tokens in memory only and never shows them in the UI.
- Backend authorization, status transitions and conflict responses remain authoritative.
- Manual accessibility and security review is still required; this is not a legal certification.

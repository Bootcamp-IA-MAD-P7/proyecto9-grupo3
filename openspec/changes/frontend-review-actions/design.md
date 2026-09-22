# Design: Human review actions

## API integration

The central API client keeps the existing in-memory bearer token flow and adds:

- `GET /comments/{comment_id}` returning the authorised `CommentDetail`.
- `POST /comments/{comment_id}/review` with `{ decision, notes? }` returning `ReviewResponse`.

No mock fallback is used. HTTP status is retained in `ApiError` so the UI can distinguish `400`, `401`, `404`, `409` and `422`. The backend remains authoritative for allowed transitions.

## TypeScript contracts

`CommentDetail` contains `comment_id`, `video_id`, `text`, `risk_score`, `uncertainty`, `model_version`, `score_source` and `status`. `ReviewDecision` is the closed union `NEEDS_REVIEW | CONFIRMED_TOXIC | NOT_TOXIC`. `ReviewResponse` contains the comment id, `REVIEWED` status, decision, reviewer and timestamp. Model signals and the human decision are separate fields.

## Interaction flow

Selection → loading detail → authorised detail → review controls → optional notes → confirmation for final decisions → submit → live feedback and updated state. `NEEDS_REVIEW` moves `PENDING` to `IN_REVIEW`; final decisions move `IN_REVIEW` to `REVIEWED`. No other transition is inferred in the frontend.

Final decisions use a native dialog pattern with `role="dialog"`, labelled/described content, explicit consequence text, Cancel and decision-specific confirm buttons. Focus moves into the dialog and returns to the triggering control after close.

## States and errors

The detail panel supports empty, loading, ready, unauthorized, not found, conflict and generic error states with retry where recovery is possible. Submission disables review controls and notes, prevents duplicate requests, preserves the selected comment context, and announces success or failure through an `aria-live` region.

## Accessibility and responsive behaviour

Use semantic sections, articles, forms, labels and native buttons. Every field has an explicit label, bounded notes validation and associated error text. Focus-visible styles, keyboard-operable controls, live feedback and non-colour status text are required. The two-column queue/detail layout collapses at narrow widths and must remain usable at 200% zoom without accidental horizontal scrolling.

## Alternatives and trade-offs

- Keep review state in `App` rather than introducing a state library: the flow is local and this is the smallest seven-day-project slice.
- Use native controls and an in-tree dialog implementation rather than a UI dependency: fewer dependencies and better keyboard semantics to audit.
- Keep server error status codes rather than normalising all errors: conflict and authorization need distinct recovery guidance.

## Observability, privacy and rollback

The UI exposes status and reviewer feedback without logging tokens or comment text. Rollback is a frontend branch revert; no backend schema or external action is changed. Manual audit must verify browser storage, network payloads, console output, keyboard focus and screen-reader announcements.

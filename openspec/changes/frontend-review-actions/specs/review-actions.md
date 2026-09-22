# Review actions specification

## Requirement: Select a queue comment

### Scenario: Selection starts detail loading
- GIVEN an authenticated moderator sees queue items
- WHEN the moderator activates a comment with keyboard or pointer
- THEN the item is selected and the detail region enters a loading state

## Requirement: Load authorised comment detail

### Scenario: Detail is loaded
- GIVEN a selected comment id and a valid in-memory access token
- WHEN the frontend calls `GET /comments/{comment_id}`
- THEN it displays the returned text only in the authorised detail view, plus risk, uncertainty, source, model version and current status

### Scenario: Detail is unavailable
- GIVEN the detail request returns `401`, `404`, a network error or another error
- WHEN the response is handled
- THEN the frontend shows a specific recoverable message and retry where appropriate without inventing comment text

## Requirement: Keep model signals separate from human decisions

### Scenario: Signals are explained
- GIVEN detail contains `risk_score`, `uncertainty`, `score_source` and `model_version`
- WHEN the detail is rendered
- THEN the UI labels them as prioritisation signals and does not present risk as a verdict or calculate new categories

## Requirement: Review supported decisions

### Scenario: Mark a pending comment for review
- GIVEN status is `PENDING`
- WHEN the moderator selects `NEEDS_REVIEW` and submits
- THEN the frontend sends that decision and reflects `IN_REVIEW` only when the backend accepts it

### Scenario: Confirm a toxic decision
- GIVEN status is `IN_REVIEW`
- WHEN the moderator selects `CONFIRMED_TOXIC`, confirms the explicit consequence and submits
- THEN the frontend sends the decision and displays the returned `REVIEWED` result

### Scenario: Confirm a non-toxic decision
- GIVEN status is `IN_REVIEW`
- WHEN the moderator selects `NOT_TOXIC`, confirms the explicit consequence and submits
- THEN the frontend sends the decision and displays the returned `REVIEWED` result

### Scenario: Invalid transition is rejected
- GIVEN the current status does not support the selected transition
- WHEN the backend rejects the request
- THEN the frontend preserves the comment context, shows the conflict or validation feedback and does not claim a new state

## Requirement: Optional notes

### Scenario: Notes are submitted
- GIVEN a visible labelled notes field with a documented maximum length
- WHEN the moderator enters a non-sensitive note within the limit
- THEN the note is sent with the review request

### Scenario: Notes are empty or too long
- GIVEN notes are optional
- WHEN the moderator leaves them empty or exceeds the maximum
- THEN empty notes are allowed and overlong notes are rejected with visible feedback and `aria-invalid`

## Requirement: Confirmation and feedback

### Scenario: Final decision confirmation
- GIVEN `CONFIRMED_TOXIC` or `NOT_TOXIC` is selected
- WHEN the confirmation opens
- THEN it identifies the selected comment, explains the consequence, provides Cancel and a specific confirm action, manages focus and allows keyboard operation

### Scenario: Review succeeds
- GIVEN the backend accepts a review
- WHEN the response is rendered
- THEN the UI shows decision, reviewer and timestamp, updates the status, and announces the result through `aria-live`

### Scenario: Duplicate submission is prevented
- GIVEN a review request is in progress
- WHEN the moderator interacts with review controls
- THEN controls are disabled, progress is visible, and no second request is sent

## Requirement: Recoverable API errors

### Scenario: Known errors
- GIVEN the API returns `400`, `401`, `404`, `409` or `422`
- WHEN the frontend handles the response
- THEN it shows actionable, non-sensitive feedback; `401` clears the session, `404` explains the item is unavailable, `409` explains stale state, and `400`/`422` expose validation guidance

## Requirement: Accessible responsive operation

### Scenario: Keyboard and screen reader use
- GIVEN a keyboard or screen-reader user
- WHEN they navigate the queue, detail, form and confirmation
- THEN native controls, logical focus, visible focus, labels, descriptions, live announcements and error associations are available without pointer-only behaviour

### Scenario: Mobile and zoom
- GIVEN a viewport or browser zoom up to 200%
- WHEN the moderator uses the review flow
- THEN content remains readable and usable without accidental horizontal scrolling or clipped controls

## Requirement: No external automated action

### Scenario: Human-only outcome
- GIVEN any review decision is submitted
- WHEN the backend responds
- THEN the frontend records only the human review result and performs no deletion, blocking, sanction, report or publication action

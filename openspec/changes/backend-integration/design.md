# Design

FastAPI serves `/ui/` and the API from one origin. A bearer token stays in JS
memory. The browser requests comment text only after claiming it. Rendering
uses `textContent` for all server-provided values.

SQLite version 5 builds on the review and supervision schema. `comments` gains
`uncertainty` and `score_source`. Version 3 is detected by column shape because
the old queue and the supervision change used that number for different layouts.
The old queue is copied transactionally into the review schema; an unknown shape
raises without changing data. Imported batches score before the write transaction
and insert atomically.

The scorer interface returns a score, uncertainty, version and source. Simulated
mode is the default demo. Model mode requires a local trusted joblib pipeline
with positive class `1` and `predict_proba`. Loading occurs once at startup;
missing or invalid artifacts fail startup. Joblib files must come from a trusted
source because deserialization executes code.

Existing `GET /comments` keeps the paginated, text-free queue contract from
step 4. `GET /comments/queue` is a UI-friendly alias, while
`GET /comments/status` exposes the status-filtered review summaries.

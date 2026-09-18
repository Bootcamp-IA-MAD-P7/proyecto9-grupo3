# Design

The `Database` object owns a resolved file path. Each `connect()` call enables
foreign keys, wraps writes in a transaction and closes the connection. Startup
checks `PRAGMA user_version` under `BEGIN IMMEDIATE`; version 0 creates users
and comments and becomes version 1. Version 1 preserves rows; unknown versions
fail closed. Future schema extensions are explicit versioned migrations.

Users have a string ID, unique username, display name, password hash, role,
active flag and timestamp. Comments have an autoincrement sequence, unique
source ID, video ID, text, status and optional reviewer assignment to a user.
The assignment never represents the comment author. The sequence supports
stable tie ordering later. This is local storage: `data/local/` is ignored.

Stdlib sqlite3 keeps the integrated path small and avoids mismatched ORM and
handwritten schemas. Parameterized queries and a connection per operation are
required in the following steps. An ORM remains a possible later refactor after
the full contract is stable. No real comment data is used in tests or docs.

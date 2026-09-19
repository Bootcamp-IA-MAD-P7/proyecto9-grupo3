"""Explicit, repeatable synthetic data for learning the comment review flow."""

from app.config import Settings
from app.database import Database


DEMO_COMMENTS = (
    ("C-DEMO-001", "V-DEMO-01", "This is a synthetic comment for review.", 0.92),
    ("C-DEMO-002", "V-DEMO-01", "Please explain your point in more detail.", 0.48),
    ("C-DEMO-003", "V-DEMO-02", "Thank you for contributing to this discussion.", 0.13),
)


def seed_demo_comments(database: Database) -> int:
    """Insert missing examples only; never reset a reviewed demo comment."""
    database.initialize()
    inserted = 0
    with database.connect() as connection:
        connection.execute("BEGIN IMMEDIATE")
        next_order = connection.execute(
            "SELECT COALESCE(MAX(source_order), 0) + 1 FROM comments"
        ).fetchone()[0]
        for comment_id, video_id, content, risk_score in DEMO_COMMENTS:
            existing = connection.execute(
                "SELECT 1 FROM comments WHERE id=?", (comment_id,)
            ).fetchone()
            if existing is not None:
                continue
            connection.execute(
                """INSERT INTO comments
                   (id, video_id, text, risk_score, model_version, source_order, status)
                   VALUES (?, ?, ?, ?, 'demo-simulated-v1', ?, 'PENDING')""",
                (comment_id, video_id, content, risk_score, next_order),
            )
            next_order += 1
            inserted += 1
    return inserted


def main() -> None:
    count = seed_demo_comments(Database(Settings().database_path))
    print(f"Synthetic demo comments inserted: {count}. Existing comments were preserved.")


if __name__ == "__main__":
    main()

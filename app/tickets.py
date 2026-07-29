"""Every question becomes a ticket — answered or not.

The refused rows plus the thumbs-down rows are the queue of guides to write
next. That loop is the point of the system.
"""

import sqlite3
import sys
from datetime import datetime, timezone
from pathlib import Path

DB_PATH = Path(__file__).parent.parent / "tickets.db"

SCHEMA = """
CREATE TABLE IF NOT EXISTS tickets (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    asked_at TEXT NOT NULL,
    source TEXT NOT NULL,            -- 'slack', 'voice', 'cli'
    question TEXT NOT NULL,
    answered INTEGER NOT NULL,       -- 1 answered, 0 refused
    reply TEXT NOT NULL,
    retrieved TEXT NOT NULL,         -- top guide section, for debugging misses
    best_distance REAL NOT NULL,
    feedback TEXT                    -- 'up', 'down', or NULL
)
"""


def _connect() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.execute(SCHEMA)
    return conn


def log_ticket(source: str, question: str, result: dict[str, object]) -> int:
    """Record one question and its outcome. Returns the ticket id."""
    with _connect() as conn:
        cursor = conn.execute(
            "INSERT INTO tickets (asked_at, source, question, answered, reply,"
            " retrieved, best_distance) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (
                datetime.now(timezone.utc).isoformat(timespec="seconds"),
                source,
                question,
                int(result["answered"]),
                result["reply"],
                result["retrieved"][0],
                result["best_distance"],
            ),
        )
        return cursor.lastrowid


def record_feedback(ticket_id: int, feedback: str) -> None:
    if feedback not in ("up", "down"):
        raise ValueError(f"feedback must be 'up' or 'down', got {feedback!r}")
    with _connect() as conn:
        conn.execute("UPDATE tickets SET feedback = ? WHERE id = ?", (feedback, ticket_id))


def report() -> str:
    """The 'what guide do I write next' report."""
    with _connect() as conn:
        total, answered = conn.execute(
            "SELECT COUNT(*), COALESCE(SUM(answered), 0) FROM tickets"
        ).fetchone()
        refused = conn.execute(
            "SELECT question, retrieved FROM tickets WHERE answered = 0"
            " ORDER BY asked_at DESC"
        ).fetchall()
        thumbs_down = conn.execute(
            "SELECT question, retrieved FROM tickets WHERE feedback = 'down'"
            " ORDER BY asked_at DESC"
        ).fetchall()

    lines = [f"Tickets: {total} total, {answered} answered, {total - answered} refused", ""]
    lines.append("Couldn't answer (write a guide for these):")
    lines += [f"  - {q!r}  (closest match was: {r})" for q, r in refused] or ["  none"]
    lines.append("")
    lines.append("Answered but unhelpful (fix these guides):")
    lines += [f"  - {q!r}  (answered from: {r})" for q, r in thumbs_down] or ["  none"]
    return "\n".join(lines)


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "report":
        print(report())
    else:
        raise SystemExit("Usage: python -m app.tickets report")

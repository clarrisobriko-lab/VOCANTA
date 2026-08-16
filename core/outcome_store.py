from __future__ import annotations

from datetime import datetime, timezone
import sqlite3

from intelligence.application_outcomes import Outcome


def ensure_outcome_schema(connection: sqlite3.Connection) -> None:
    connection.execute("""
        CREATE TABLE IF NOT EXISTS application_outcomes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            job_id INTEGER NOT NULL,
            status TEXT NOT NULL,
            applied INTEGER NOT NULL DEFAULT 0,
            retry_later INTEGER NOT NULL DEFAULT 0,
            human_required INTEGER NOT NULL DEFAULT 0,
            confidence INTEGER NOT NULL DEFAULT 0,
            reason TEXT NOT NULL DEFAULT '',
            recorded_at TEXT NOT NULL,
            FOREIGN KEY(job_id) REFERENCES jobs(id) ON DELETE CASCADE
        )
    """)
    connection.execute("CREATE INDEX IF NOT EXISTS idx_application_outcomes_job_id ON application_outcomes(job_id)")
    connection.execute("CREATE INDEX IF NOT EXISTS idx_application_outcomes_status ON application_outcomes(status)")
    connection.commit()


def record_outcome(connection: sqlite3.Connection, job_id: int, outcome: Outcome) -> None:
    ensure_outcome_schema(connection)
    now = datetime.now(timezone.utc).isoformat()
    connection.execute(
        "INSERT INTO application_outcomes(job_id,status,applied,retry_later,human_required,confidence,reason,recorded_at) VALUES(?,?,?,?,?,?,?,?)",
        (job_id, outcome.status, int(outcome.applied), int(outcome.retry_later), int(outcome.human_required), outcome.confidence, outcome.reason, now),
    )
    if outcome.applied:
        connection.execute("UPDATE jobs SET applied=1,status='APPLIED',applied_date=COALESCE(applied_date,?),updated_at=? WHERE id=?", (now, now, job_id))
    connection.commit()


def outcome_statistics(connection: sqlite3.Connection) -> dict[str, int]:
    ensure_outcome_schema(connection)
    rows = connection.execute("SELECT status, COUNT(*) AS total FROM application_outcomes GROUP BY status").fetchall()
    stats = {str(row[0]).lower(): int(row[1]) for row in rows}
    stats["human_required"] = int(connection.execute("SELECT COUNT(*) FROM application_outcomes WHERE human_required=1").fetchone()[0])
    stats["retry_later"] = int(connection.execute("SELECT COUNT(*) FROM application_outcomes WHERE retry_later=1").fetchone()[0])
    return stats

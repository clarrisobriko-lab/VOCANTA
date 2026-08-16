from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
import sqlite3


@dataclass(frozen=True, slots=True)
class RetryCandidate:
    job_id: int
    attempts: int
    next_retry_at: str


def ensure_retry_schema(connection: sqlite3.Connection) -> None:
    connection.execute("""
        CREATE TABLE IF NOT EXISTS application_retry_queue (
            job_id INTEGER PRIMARY KEY,
            attempts INTEGER NOT NULL DEFAULT 0,
            next_retry_at TEXT NOT NULL,
            last_reason TEXT NOT NULL DEFAULT '',
            retired INTEGER NOT NULL DEFAULT 0,
            updated_at TEXT NOT NULL,
            FOREIGN KEY(job_id) REFERENCES jobs(id) ON DELETE CASCADE
        )
    """)
    connection.execute("CREATE INDEX IF NOT EXISTS idx_retry_due ON application_retry_queue(retired,next_retry_at)")
    connection.commit()


def schedule_retry(connection: sqlite3.Connection, job_id: int, reason: str, *, cooldown_seconds: int = 300, max_attempts: int = 3, now: datetime | None = None) -> bool:
    ensure_retry_schema(connection)
    now = now or datetime.now(timezone.utc)
    row = connection.execute("SELECT attempts,retired FROM application_retry_queue WHERE job_id=?", (job_id,)).fetchone()
    attempts = (int(row[0]) if row else 0) + 1
    retired = attempts >= max_attempts
    next_retry = now + timedelta(seconds=cooldown_seconds)
    connection.execute(
        "INSERT INTO application_retry_queue(job_id,attempts,next_retry_at,last_reason,retired,updated_at) VALUES(?,?,?,?,?,?) ON CONFLICT(job_id) DO UPDATE SET attempts=excluded.attempts,next_retry_at=excluded.next_retry_at,last_reason=excluded.last_reason,retired=excluded.retired,updated_at=excluded.updated_at",
        (job_id, attempts, next_retry.isoformat(), reason, int(retired), now.isoformat()),
    )
    connection.commit()
    return not retired


def due_retries(connection: sqlite3.Connection, *, limit: int = 10, now: datetime | None = None) -> list[RetryCandidate]:
    ensure_retry_schema(connection)
    now = (now or datetime.now(timezone.utc)).isoformat()
    rows = connection.execute("SELECT job_id,attempts,next_retry_at FROM application_retry_queue WHERE retired=0 AND next_retry_at<=? ORDER BY next_retry_at LIMIT ?", (now, limit)).fetchall()
    return [RetryCandidate(int(r[0]), int(r[1]), str(r[2])) for r in rows]


def retire_retry(connection: sqlite3.Connection, job_id: int, reason: str = "terminal outcome") -> None:
    ensure_retry_schema(connection)
    connection.execute("UPDATE application_retry_queue SET retired=1,last_reason=?,updated_at=? WHERE job_id=?", (reason, datetime.now(timezone.utc).isoformat(), job_id))
    connection.commit()


def clear_retry(connection: sqlite3.Connection, job_id: int) -> None:
    ensure_retry_schema(connection)
    connection.execute("DELETE FROM application_retry_queue WHERE job_id=?", (job_id,))
    connection.commit()

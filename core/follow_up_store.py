from __future__ import annotations

from datetime import datetime, timezone
import sqlite3

from intelligence.follow_up import evaluate_follow_up


def ensure_follow_up_schema(connection: sqlite3.Connection) -> None:
    connection.execute("""
        CREATE TABLE IF NOT EXISTS application_follow_ups (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            job_id INTEGER NOT NULL,
            action TEXT NOT NULL,
            due_at TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'PENDING',
            created_at TEXT NOT NULL,
            completed_at TEXT,
            UNIQUE(job_id, action),
            FOREIGN KEY(job_id) REFERENCES jobs(id) ON DELETE CASCADE
        )
    """)
    connection.execute("CREATE INDEX IF NOT EXISTS idx_followups_due ON application_follow_ups(status,due_at)")
    connection.commit()


def generate_follow_up_queue(connection: sqlite3.Connection, *, now: datetime | None = None) -> int:
    ensure_follow_up_schema(connection); now = now or datetime.now(timezone.utc); created = 0
    rows = connection.execute("SELECT id,status,applied_date FROM jobs WHERE applied=1 AND applied_date IS NOT NULL").fetchall()
    for row in rows:
        count = int(connection.execute("SELECT COUNT(*) FROM application_follow_ups WHERE job_id=? AND status='COMPLETED'", (row[0],)).fetchone()[0])
        decision = evaluate_follow_up(str(row[2]), status=str(row[1]), follow_up_count=count, now=now)
        if not decision.due: continue
        cursor = connection.execute("INSERT OR IGNORE INTO application_follow_ups(job_id,action,due_at,status,created_at) VALUES(?,?,?,?,?)", (row[0], decision.action, decision.due_at, "PENDING", now.isoformat()))
        created += max(0, cursor.rowcount)
    connection.commit(); return created


def due_follow_ups(connection: sqlite3.Connection, *, now: datetime | None = None, limit: int = 20):
    ensure_follow_up_schema(connection); stamp=(now or datetime.now(timezone.utc)).isoformat()
    return connection.execute("SELECT f.*,j.company,j.title,j.url FROM application_follow_ups f JOIN jobs j ON j.id=f.job_id WHERE f.status='PENDING' AND f.due_at<=? ORDER BY f.due_at LIMIT ?", (stamp,limit)).fetchall()


def complete_follow_up(connection: sqlite3.Connection, follow_up_id: int, *, now: datetime | None = None) -> None:
    ensure_follow_up_schema(connection); stamp=(now or datetime.now(timezone.utc)).isoformat()
    connection.execute("UPDATE application_follow_ups SET status='COMPLETED',completed_at=? WHERE id=?", (stamp,follow_up_id)); connection.commit()


def cancel_job_follow_ups(connection: sqlite3.Connection, job_id: int) -> None:
    ensure_follow_up_schema(connection)
    connection.execute("UPDATE application_follow_ups SET status='CANCELLED' WHERE job_id=? AND status='PENDING'", (job_id,)); connection.commit()

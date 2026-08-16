from __future__ import annotations

from datetime import datetime, timedelta, timezone
import sqlite3

from intelligence.follow_up import evaluate_follow_up


def ensure_follow_up_schema(connection: sqlite3.Connection) -> None:
    connection.execute("""CREATE TABLE IF NOT EXISTS application_follow_ups (
        id INTEGER PRIMARY KEY AUTOINCREMENT, job_id INTEGER NOT NULL, action TEXT NOT NULL,
        due_at TEXT NOT NULL, status TEXT NOT NULL DEFAULT 'PENDING', created_at TEXT NOT NULL,
        completed_at TEXT, attempts INTEGER NOT NULL DEFAULT 0, last_attempt_at TEXT,
        next_attempt_at TEXT, last_error TEXT NOT NULL DEFAULT '', delivery_id TEXT NOT NULL DEFAULT '',
        UNIQUE(job_id, action), FOREIGN KEY(job_id) REFERENCES jobs(id) ON DELETE CASCADE)""")
    columns={row[1] for row in connection.execute("PRAGMA table_info(application_follow_ups)")}
    migrations={"attempts":"INTEGER NOT NULL DEFAULT 0","last_attempt_at":"TEXT","next_attempt_at":"TEXT","last_error":"TEXT NOT NULL DEFAULT ''","delivery_id":"TEXT NOT NULL DEFAULT ''"}
    for name,spec in migrations.items():
        if name not in columns: connection.execute(f"ALTER TABLE application_follow_ups ADD COLUMN {name} {spec}")
    connection.execute("CREATE INDEX IF NOT EXISTS idx_followups_due ON application_follow_ups(status,due_at)")
    connection.commit()


def generate_follow_up_queue(connection: sqlite3.Connection, *, now: datetime | None = None) -> int:
    ensure_follow_up_schema(connection); now=now or datetime.now(timezone.utc); created=0
    for row in connection.execute("SELECT id,status,applied_date FROM jobs WHERE applied=1 AND applied_date IS NOT NULL").fetchall():
        count=int(connection.execute("SELECT COUNT(*) FROM application_follow_ups WHERE job_id=? AND status='COMPLETED'",(row[0],)).fetchone()[0])
        decision=evaluate_follow_up(str(row[2]),status=str(row[1]),follow_up_count=count,now=now)
        if decision.due:
            cursor=connection.execute("INSERT OR IGNORE INTO application_follow_ups(job_id,action,due_at,status,created_at,next_attempt_at) VALUES(?,?,?,?,?,?)",(row[0],decision.action,decision.due_at,"PENDING",now.isoformat(),decision.due_at)); created+=max(0,cursor.rowcount)
    connection.commit(); return created


def due_follow_ups(connection: sqlite3.Connection, *, now: datetime | None = None, limit: int = 20):
    ensure_follow_up_schema(connection); stamp=(now or datetime.now(timezone.utc)).isoformat()
    return connection.execute("SELECT f.*,j.company,j.title,j.url FROM application_follow_ups f JOIN jobs j ON j.id=f.job_id WHERE f.status='PENDING' AND f.due_at<=? AND (f.next_attempt_at IS NULL OR f.next_attempt_at<=?) ORDER BY COALESCE(f.next_attempt_at,f.due_at) LIMIT ?",(stamp,stamp,limit)).fetchall()


def complete_follow_up(connection: sqlite3.Connection, follow_up_id: int, *, delivery_id: str='', now: datetime | None = None) -> None:
    ensure_follow_up_schema(connection); stamp=(now or datetime.now(timezone.utc)).isoformat()
    connection.execute("UPDATE application_follow_ups SET status='COMPLETED',completed_at=?,delivery_id=?,last_error='' WHERE id=? AND status='PENDING'",(stamp,delivery_id,follow_up_id)); connection.commit()


def record_follow_up_failure(connection: sqlite3.Connection, follow_up_id: int, error: str, *, max_attempts: int=3, retry_minutes: int=60, now: datetime | None=None) -> bool:
    ensure_follow_up_schema(connection); now=now or datetime.now(timezone.utc)
    row=connection.execute("SELECT attempts,status FROM application_follow_ups WHERE id=?",(follow_up_id,)).fetchone()
    if row is None or row[1] != 'PENDING': return False
    attempts=int(row[0])+1; retry=attempts < max_attempts
    connection.execute("UPDATE application_follow_ups SET attempts=?,last_attempt_at=?,next_attempt_at=?,last_error=?,status=? WHERE id=?",(attempts,now.isoformat(),(now+timedelta(minutes=retry_minutes)).isoformat() if retry else None,error,'PENDING' if retry else 'FAILED',follow_up_id)); connection.commit(); return retry


def follow_up_statistics(connection: sqlite3.Connection) -> dict[str,int]:
    ensure_follow_up_schema(connection)
    rows=connection.execute("SELECT status,COUNT(*) FROM application_follow_ups GROUP BY status").fetchall()
    stats={str(status).lower():int(total) for status,total in rows}
    for key in ('pending','completed','failed','cancelled'): stats.setdefault(key,0)
    return stats


def cancel_job_follow_ups(connection: sqlite3.Connection, job_id: int) -> None:
    ensure_follow_up_schema(connection); connection.execute("UPDATE application_follow_ups SET status='CANCELLED' WHERE job_id=? AND status='PENDING'",(job_id,)); connection.commit()

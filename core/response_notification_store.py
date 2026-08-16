from __future__ import annotations

from datetime import datetime, timedelta, timezone

MAX_ATTEMPTS=3
RETRY_MINUTES=30


def ensure_notification_schema(connection) -> None:
    connection.execute("CREATE TABLE IF NOT EXISTS response_notifications(message_id TEXT PRIMARY KEY,priority TEXT NOT NULL,status TEXT NOT NULL DEFAULT 'PENDING',created_at TEXT NOT NULL,delivered_at TEXT,attempts INTEGER NOT NULL DEFAULT 0,next_attempt_at TEXT,last_error TEXT)")
    columns={row[1] for row in connection.execute("PRAGMA table_info(response_notifications)").fetchall()}
    for name,definition in (("attempts","INTEGER NOT NULL DEFAULT 0"),("next_attempt_at","TEXT"),("last_error","TEXT")):
        if name not in columns: connection.execute(f"ALTER TABLE response_notifications ADD COLUMN {name} {definition}")
    connection.commit()


def claim_notification(connection,message_id: str,priority: str,*,now=None) -> bool:
    ensure_notification_schema(connection); stamp=(now or datetime.now(timezone.utc)).isoformat()
    connection.execute("INSERT OR IGNORE INTO response_notifications(message_id,priority,status,created_at) VALUES(?,?,?,?)",(message_id,priority,'PENDING',stamp)); connection.commit()
    row=connection.execute("SELECT status,attempts,next_attempt_at FROM response_notifications WHERE message_id=?",(message_id,)).fetchone()
    if row is None or row[0]!='PENDING' or int(row[1])>=MAX_ATTEMPTS: return False
    return not row[2] or row[2]<=stamp


def mark_notification_failed(connection,message_id: str,error: str,*,now=None) -> None:
    current=now or datetime.now(timezone.utc); row=connection.execute("SELECT attempts FROM response_notifications WHERE message_id=?",(message_id,)).fetchone(); attempts=(int(row[0]) if row else 0)+1
    status='FAILED' if attempts>=MAX_ATTEMPTS else 'PENDING'; next_attempt=None if status=='FAILED' else (current+timedelta(minutes=RETRY_MINUTES*attempts)).isoformat()
    connection.execute("UPDATE response_notifications SET status=?,attempts=?,next_attempt_at=?,last_error=? WHERE message_id=?",(status,attempts,next_attempt,str(error)[:500],message_id)); connection.commit()


def mark_notification_delivered(connection,message_id: str,*,now=None) -> None:
    stamp=(now or datetime.now(timezone.utc)).isoformat()
    connection.execute("UPDATE response_notifications SET status='DELIVERED',delivered_at=?,next_attempt_at=NULL,last_error=NULL WHERE message_id=?",(stamp,message_id)); connection.commit()

from __future__ import annotations

from datetime import datetime, timezone


def ensure_notification_schema(connection) -> None:
    connection.execute("CREATE TABLE IF NOT EXISTS response_notifications(message_id TEXT PRIMARY KEY,priority TEXT NOT NULL,status TEXT NOT NULL DEFAULT 'PENDING',created_at TEXT NOT NULL,delivered_at TEXT)")
    connection.commit()


def claim_notification(connection,message_id: str,priority: str,*,now=None) -> bool:
    ensure_notification_schema(connection); stamp=(now or datetime.now(timezone.utc)).isoformat()
    cursor=connection.execute("INSERT OR IGNORE INTO response_notifications(message_id,priority,status,created_at) VALUES(?,?,?,?)",(message_id,priority,'PENDING',stamp)); connection.commit()
    return cursor.rowcount==1


def mark_notification_delivered(connection,message_id: str,*,now=None) -> None:
    stamp=(now or datetime.now(timezone.utc)).isoformat()
    connection.execute("UPDATE response_notifications SET status='DELIVERED',delivered_at=? WHERE message_id=?",(stamp,message_id)); connection.commit()

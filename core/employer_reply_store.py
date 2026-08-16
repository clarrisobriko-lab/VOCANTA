from __future__ import annotations

from datetime import datetime, timezone

from intelligence.employer_reply_drafts import ReplyDraft


def ensure_reply_schema(connection) -> None:
    connection.execute("CREATE TABLE IF NOT EXISTS employer_reply_drafts(message_id TEXT PRIMARY KEY,job_id INTEGER NOT NULL,subject TEXT NOT NULL,body TEXT NOT NULL,status TEXT NOT NULL DEFAULT 'AWAITING_APPROVAL',created_at TEXT NOT NULL,approved_at TEXT,sent_at TEXT)")
    connection.commit()


def save_reply_draft(connection,message_id: str,job_id: int,draft: ReplyDraft,*,now=None) -> bool:
    ensure_reply_schema(connection); stamp=(now or datetime.now(timezone.utc)).isoformat()
    cursor=connection.execute("INSERT OR IGNORE INTO employer_reply_drafts(message_id,job_id,subject,body,status,created_at) VALUES(?,?,?,?,?,?)",(message_id,job_id,draft.subject,draft.body,'AWAITING_APPROVAL',stamp)); connection.commit()
    return cursor.rowcount==1


def approve_reply_draft(connection,message_id: str,*,now=None) -> bool:
    stamp=(now or datetime.now(timezone.utc)).isoformat()
    cursor=connection.execute("UPDATE employer_reply_drafts SET status='APPROVED',approved_at=? WHERE message_id=? AND status='AWAITING_APPROVAL'",(stamp,message_id)); connection.commit()
    return cursor.rowcount==1

from __future__ import annotations

from datetime import datetime, timezone

from intelligence.employer_reply_drafts import ReplyDraft


def ensure_reply_schema(connection) -> None:
    connection.execute("CREATE TABLE IF NOT EXISTS employer_reply_drafts(message_id TEXT PRIMARY KEY,job_id INTEGER NOT NULL,subject TEXT NOT NULL,body TEXT NOT NULL,status TEXT NOT NULL DEFAULT 'AWAITING_APPROVAL',created_at TEXT NOT NULL,approved_at TEXT,sent_at TEXT,last_error TEXT)")
    columns={r[1] for r in connection.execute("PRAGMA table_info(employer_reply_drafts)").fetchall()}
    for name in ('approved_at','sent_at','last_error'):
        if name not in columns:
            connection.execute(f"ALTER TABLE employer_reply_drafts ADD COLUMN {name} TEXT")
    connection.commit()


def save_reply_draft(connection,message_id: str,job_id: int,draft: ReplyDraft,*,now=None) -> bool:
    ensure_reply_schema(connection); stamp=(now or datetime.now(timezone.utc)).isoformat(); cursor=connection.execute("INSERT OR IGNORE INTO employer_reply_drafts(message_id,job_id,subject,body,status,created_at) VALUES(?,?,?,?,?,?)",(message_id,job_id,draft.subject,draft.body,'AWAITING_APPROVAL',stamp)); connection.commit(); return cursor.rowcount==1


def update_reply_draft(connection,message_id: str,subject: str,body: str) -> bool:
    ensure_reply_schema(connection)
    subject=subject.strip(); body=body.strip()
    if not subject or not body: return False
    cursor=connection.execute("UPDATE employer_reply_drafts SET subject=?,body=?,last_error=NULL WHERE message_id=? AND status='AWAITING_APPROVAL'",(subject,body,message_id)); connection.commit(); return cursor.rowcount==1


def approve_reply_draft(connection,message_id: str,*,now=None) -> bool:
    ensure_reply_schema(connection); stamp=(now or datetime.now(timezone.utc)).isoformat(); cursor=connection.execute("UPDATE employer_reply_drafts SET status='APPROVED',approved_at=?,last_error=NULL WHERE message_id=? AND status='AWAITING_APPROVAL'",(stamp,message_id)); connection.commit(); return cursor.rowcount==1


def mark_reply_sent(connection,message_id: str,*,now=None) -> None:
    ensure_reply_schema(connection); stamp=(now or datetime.now(timezone.utc)).isoformat(); connection.execute("UPDATE employer_reply_drafts SET status='SENT',sent_at=?,last_error=NULL WHERE message_id=? AND status='APPROVED'",(stamp,message_id)); connection.commit()


def mark_reply_send_failed(connection,message_id: str,error: str) -> None:
    ensure_reply_schema(connection); connection.execute("UPDATE employer_reply_drafts SET last_error=? WHERE message_id=? AND status='APPROVED'",(str(error)[:500],message_id)); connection.commit()

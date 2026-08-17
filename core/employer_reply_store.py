from __future__ import annotations

from datetime import datetime, timedelta, timezone

from intelligence.employer_reply_drafts import ReplyDraft

SEND_CLAIM_MINUTES=10


def _stamp(now=None): return (now or datetime.now(timezone.utc)).isoformat()


def ensure_reply_schema(connection) -> None:
    connection.execute("CREATE TABLE IF NOT EXISTS employer_reply_drafts(message_id TEXT PRIMARY KEY,job_id INTEGER NOT NULL,subject TEXT NOT NULL,body TEXT NOT NULL,status TEXT NOT NULL DEFAULT 'AWAITING_APPROVAL',created_at TEXT NOT NULL,approved_at TEXT,sent_at TEXT,last_error TEXT,send_claimed_at TEXT,gmail_sent_message_id TEXT,archived_at TEXT)")
    columns={r[1] for r in connection.execute("PRAGMA table_info(employer_reply_drafts)").fetchall()}
    migrations=(('job_id','INTEGER'),('created_at','TEXT'),('approved_at','TEXT'),('sent_at','TEXT'),('last_error','TEXT'),('send_claimed_at','TEXT'),('gmail_sent_message_id','TEXT'),('archived_at','TEXT'))
    for name,column_type in migrations:
        if name not in columns:
            connection.execute(f"ALTER TABLE employer_reply_drafts ADD COLUMN {name} {column_type}")
            columns.add(name)
    connection.execute("CREATE TABLE IF NOT EXISTS employer_reply_audit(id INTEGER PRIMARY KEY AUTOINCREMENT,message_id TEXT NOT NULL,event TEXT NOT NULL,detail TEXT NOT NULL DEFAULT '',created_at TEXT NOT NULL)")
    connection.execute("CREATE INDEX IF NOT EXISTS idx_reply_status_archive_created ON employer_reply_drafts(status,archived_at,created_at DESC)")
    connection.execute("CREATE INDEX IF NOT EXISTS idx_reply_status_archive_sent ON employer_reply_drafts(status,archived_at,sent_at DESC)")
    connection.execute("CREATE INDEX IF NOT EXISTS idx_reply_status_claim ON employer_reply_drafts(status,send_claimed_at)")
    connection.execute("CREATE INDEX IF NOT EXISTS idx_reply_job ON employer_reply_drafts(job_id)")
    connection.execute("CREATE INDEX IF NOT EXISTS idx_reply_gmail_message ON employer_reply_drafts(gmail_sent_message_id)")
    connection.execute("CREATE INDEX IF NOT EXISTS idx_reply_audit_message_id ON employer_reply_audit(message_id,id DESC)")
    connection.execute("CREATE INDEX IF NOT EXISTS idx_reply_audit_created ON employer_reply_audit(created_at DESC)")
    connection.commit()


def record_reply_event(connection,message_id: str,event: str,detail: str='',*,now=None) -> None:
    ensure_reply_schema(connection); connection.execute("INSERT INTO employer_reply_audit(message_id,event,detail,created_at) VALUES(?,?,?,?)",(message_id,event,detail[:1000],_stamp(now))); connection.commit()


def save_reply_draft(connection,message_id: str,job_id: int,draft: ReplyDraft,*,now=None) -> bool:
    ensure_reply_schema(connection); stamp=_stamp(now); cursor=connection.execute("INSERT OR IGNORE INTO employer_reply_drafts(message_id,job_id,subject,body,status,created_at) VALUES(?,?,?,?,?,?)",(message_id,job_id,draft.subject,draft.body,'AWAITING_APPROVAL',stamp)); connection.commit()
    if cursor.rowcount==1: record_reply_event(connection,message_id,'CREATED',draft.subject,now=now)
    return cursor.rowcount==1


def update_reply_draft(connection,message_id: str,subject: str,body: str,*,now=None) -> bool:
    ensure_reply_schema(connection); subject=subject.strip(); body=body.strip()
    if not subject or not body: return False
    cursor=connection.execute("UPDATE employer_reply_drafts SET subject=?,body=?,last_error=NULL WHERE message_id=? AND status='AWAITING_APPROVAL' AND archived_at IS NULL",(subject,body,message_id)); connection.commit()
    if cursor.rowcount==1: record_reply_event(connection,message_id,'EDITED',subject,now=now)
    return cursor.rowcount==1


def approve_reply_draft(connection,message_id: str,*,now=None) -> bool:
    ensure_reply_schema(connection); stamp=_stamp(now); cursor=connection.execute("UPDATE employer_reply_drafts SET status='APPROVED',approved_at=?,last_error=NULL WHERE message_id=? AND status='AWAITING_APPROVAL' AND archived_at IS NULL",(stamp,message_id)); connection.commit()
    if cursor.rowcount==1: record_reply_event(connection,message_id,'APPROVED',now=now)
    return cursor.rowcount==1


def archive_reply(connection,message_id: str,*,now=None) -> bool:
    ensure_reply_schema(connection); stamp=_stamp(now); cursor=connection.execute("UPDATE employer_reply_drafts SET archived_at=? WHERE message_id=? AND status='SENT' AND archived_at IS NULL",(stamp,message_id)); connection.commit()
    if cursor.rowcount==1: record_reply_event(connection,message_id,'ARCHIVED',now=now)
    return cursor.rowcount==1


def restore_reply(connection,message_id: str,*,now=None) -> bool:
    ensure_reply_schema(connection); cursor=connection.execute("UPDATE employer_reply_drafts SET archived_at=NULL WHERE message_id=? AND status='SENT' AND archived_at IS NOT NULL",(message_id,)); connection.commit()
    if cursor.rowcount==1: record_reply_event(connection,message_id,'RESTORED',now=now)
    return cursor.rowcount==1


def recover_stale_reply_sends(connection,*,now=None,minutes=SEND_CLAIM_MINUTES) -> int:
    ensure_reply_schema(connection); current=now or datetime.now(timezone.utc); cutoff=(current-timedelta(minutes=minutes)).isoformat()
    rows=connection.execute("SELECT message_id FROM employer_reply_drafts WHERE status='SENDING' AND archived_at IS NULL AND (send_claimed_at IS NULL OR send_claimed_at<=?)",(cutoff,)).fetchall()
    for row in rows:
        message_id=str(row[0]); connection.execute("UPDATE employer_reply_drafts SET status='APPROVED',send_claimed_at=NULL,last_error='Recovered stale send claim' WHERE message_id=? AND status='SENDING'",(message_id,)); connection.commit(); record_reply_event(connection,message_id,'SEND_RECOVERED','Stale send claim released',now=current)
    return len(rows)


def claim_reply_send(connection,message_id: str,*,now=None) -> bool:
    ensure_reply_schema(connection); current=now or datetime.now(timezone.utc); recover_stale_reply_sends(connection,now=current)
    cursor=connection.execute("UPDATE employer_reply_drafts SET status='SENDING',send_claimed_at=?,last_error=NULL WHERE message_id=? AND status='APPROVED' AND archived_at IS NULL",(_stamp(current),message_id)); connection.commit()
    if cursor.rowcount==1: record_reply_event(connection,message_id,'SEND_CLAIMED',now=current)
    return cursor.rowcount==1


def mark_reply_sent(connection,message_id: str,gmail_message_id: str='',*,now=None) -> None:
    ensure_reply_schema(connection); stamp=_stamp(now); gmail_message_id=str(gmail_message_id or '').strip(); cursor=connection.execute("UPDATE employer_reply_drafts SET status='SENT',sent_at=?,send_claimed_at=NULL,last_error=NULL,gmail_sent_message_id=? WHERE message_id=? AND status='SENDING' AND archived_at IS NULL",(stamp,gmail_message_id,message_id)); connection.commit()
    if cursor.rowcount==1:
        if gmail_message_id: record_reply_event(connection,message_id,'GMAIL_ACCEPTED',gmail_message_id,now=now)
        record_reply_event(connection,message_id,'SENT',gmail_message_id,now=now)


def mark_reply_send_failed(connection,message_id: str,error: str,*,now=None) -> None:
    ensure_reply_schema(connection); detail=str(error)[:500]; cursor=connection.execute("UPDATE employer_reply_drafts SET status='APPROVED',send_claimed_at=NULL,last_error=? WHERE message_id=? AND status='SENDING' AND archived_at IS NULL",(detail,message_id)); connection.commit()
    if cursor.rowcount==1: record_reply_event(connection,message_id,'SEND_FAILED',detail,now=now)

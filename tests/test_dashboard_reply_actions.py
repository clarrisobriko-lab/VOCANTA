import sqlite3

from analytics import reply_drafts
from core.employer_reply_store import approve_reply_draft, ensure_reply_schema


def connection():
    c=sqlite3.connect(':memory:')
    c.execute("CREATE TABLE jobs(id INTEGER PRIMARY KEY,company TEXT,title TEXT)")
    c.execute("INSERT INTO jobs VALUES(1,'Acme','Counsel')")
    ensure_reply_schema(c)
    c.execute("INSERT INTO employer_reply_drafts(message_id,job_id,subject,body,status,created_at) VALUES('m1',1,'Re: Interview','Thank you','AWAITING_APPROVAL','2026-08-16T00:00:00+00:00')")
    c.commit()
    return c


def test_dashboard_lists_only_awaiting_drafts_for_approval():
    c=connection()
    pending=reply_drafts(c,'AWAITING_APPROVAL')
    approved=reply_drafts(c,'APPROVED')
    assert [item['message_id'] for item in pending]==['m1']
    assert approved==[]


def test_approval_moves_draft_into_send_queue():
    c=connection()
    assert approve_reply_draft(c,'m1')
    assert reply_drafts(c,'AWAITING_APPROVAL')==[]
    approved=reply_drafts(c,'APPROVED')
    assert [item['message_id'] for item in approved]==['m1']

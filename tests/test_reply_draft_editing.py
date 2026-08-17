import sqlite3

from core.employer_reply_store import approve_reply_draft, ensure_reply_schema, update_reply_draft


def connection():
    c=sqlite3.connect(':memory:')
    ensure_reply_schema(c)
    c.execute("INSERT INTO employer_reply_drafts(message_id,job_id,subject,body,status,created_at) VALUES('m1',1,'Old subject','Old body','AWAITING_APPROVAL','2026-08-17T00:00:00+00:00')")
    c.commit()
    return c


def test_pending_draft_can_be_edited():
    c=connection()
    assert update_reply_draft(c,'m1','Re: Interview times','Thank you. Tuesday works for me.')
    row=c.execute("SELECT subject,body FROM employer_reply_drafts WHERE message_id='m1'").fetchone()
    assert row==('Re: Interview times','Thank you. Tuesday works for me.')


def test_blank_edit_is_rejected():
    c=connection()
    assert update_reply_draft(c,'m1','','Body') is False
    assert update_reply_draft(c,'m1','Subject','') is False


def test_approved_draft_is_locked_against_edits():
    c=connection()
    assert approve_reply_draft(c,'m1')
    assert update_reply_draft(c,'m1','Changed','Changed') is False
    row=c.execute("SELECT subject,body FROM employer_reply_drafts WHERE message_id='m1'").fetchone()
    assert row==('Old subject','Old body')

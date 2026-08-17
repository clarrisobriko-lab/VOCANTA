import sqlite3
from datetime import datetime, timedelta, timezone

from core.employer_reply_store import claim_reply_send, recover_stale_reply_sends, save_reply_draft, approve_reply_draft
from intelligence.employer_reply_drafts import build_reply_draft


def test_stale_send_claim_returns_to_approved():
    c=sqlite3.connect(':memory:'); draft=build_reply_draft('INTERVIEW','Acme','Counsel','Candidate','Interview'); save_reply_draft(c,'m1',1,draft); approve_reply_draft(c,'m1')
    old=datetime.now(timezone.utc)-timedelta(minutes=20)
    assert claim_reply_send(c,'m1',now=old)
    assert recover_stale_reply_sends(c,now=datetime.now(timezone.utc))==1
    row=c.execute("SELECT status,send_claimed_at,last_error FROM employer_reply_drafts WHERE message_id='m1'").fetchone()
    assert row[0]=='APPROVED'
    assert row[1] is None
    assert row[2]=='Recovered stale send claim'
    assert c.execute("SELECT COUNT(*) FROM employer_reply_audit WHERE message_id='m1' AND event='SEND_RECOVERED'").fetchone()[0]==1


def test_fresh_send_claim_is_not_recovered():
    c=sqlite3.connect(':memory:'); draft=build_reply_draft('OFFER','Acme','Counsel','Candidate','Offer'); save_reply_draft(c,'m1',1,draft); approve_reply_draft(c,'m1'); now=datetime.now(timezone.utc)
    assert claim_reply_send(c,'m1',now=now)
    assert recover_stale_reply_sends(c,now=now+timedelta(minutes=5))==0
    assert c.execute("SELECT status FROM employer_reply_drafts WHERE message_id='m1'").fetchone()[0]=='SENDING'

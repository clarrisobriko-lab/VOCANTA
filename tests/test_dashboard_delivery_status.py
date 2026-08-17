import sqlite3

from analytics import delivered_replies
from core.employer_reply_store import approve_reply_draft, claim_reply_send, mark_reply_sent, save_reply_draft
from intelligence.employer_reply_drafts import build_reply_draft


def test_dashboard_surfaces_gmail_delivery_identifier():
    c=sqlite3.connect(':memory:')
    c.execute("CREATE TABLE jobs(id INTEGER PRIMARY KEY,company TEXT,title TEXT)")
    c.execute("INSERT INTO jobs VALUES(1,'Acme','Counsel')")
    draft=build_reply_draft('INTERVIEW','Acme','Counsel','Candidate','Interview')
    save_reply_draft(c,'m1',1,draft); approve_reply_draft(c,'m1'); claim_reply_send(c,'m1'); mark_reply_sent(c,'m1','gmail_sent_123')
    rows=delivered_replies(c)
    assert len(rows)==1
    assert rows[0]['delivery_status']=='Gmail accepted'
    assert rows[0]['gmail_message_id']=='gmail_sent_123'
    assert rows[0]['company']=='Acme'

import sqlite3

from analytics import delivered_replies, reply_audit
from core.employer_reply_store import approve_reply_draft, archive_reply, claim_reply_send, mark_reply_sent, save_reply_draft
from intelligence.employer_reply_drafts import build_reply_draft


def test_sent_reply_can_be_archived_without_losing_audit_history():
    c=sqlite3.connect(':memory:')
    c.execute("CREATE TABLE jobs(id INTEGER PRIMARY KEY,company TEXT,title TEXT)")
    c.execute("INSERT INTO jobs VALUES(1,'Acme','Counsel')")
    draft=build_reply_draft('INTERVIEW','Acme','Counsel','Candidate','Interview')
    save_reply_draft(c,'m1',1,draft); approve_reply_draft(c,'m1'); claim_reply_send(c,'m1'); mark_reply_sent(c,'m1','gmail123')
    assert len(delivered_replies(c))==1
    assert archive_reply(c,'m1')
    assert delivered_replies(c)==[]
    events=[item['event'] for item in reply_audit(c)]
    assert 'ARCHIVED' in events
    assert 'SENT' in events
    assert 'GMAIL_ACCEPTED' in events
    assert not archive_reply(c,'m1')

import sqlite3

from analytics import delivered_replies
from core.employer_reply_store import approve_reply_draft, archive_reply, claim_reply_send, mark_reply_sent, restore_reply, save_reply_draft
from intelligence.employer_reply_drafts import build_reply_draft


def test_archived_reply_can_be_restored_to_delivered_view():
    c=sqlite3.connect(':memory:')
    c.execute("CREATE TABLE jobs(id INTEGER PRIMARY KEY,company TEXT,title TEXT)")
    c.execute("INSERT INTO jobs VALUES(1,'Acme','Counsel')")
    draft=build_reply_draft('INTERVIEW','Acme','Counsel','Candidate','Interview')
    save_reply_draft(c,'m1',1,draft); approve_reply_draft(c,'m1'); claim_reply_send(c,'m1'); mark_reply_sent(c,'m1','gmail123'); archive_reply(c,'m1')
    assert delivered_replies(c)==[]
    assert [item['message_id'] for item in delivered_replies(c,archived=True)]==['m1']
    assert restore_reply(c,'m1')
    assert [item['message_id'] for item in delivered_replies(c)]==['m1']
    assert delivered_replies(c,archived=True)==[]
    assert c.execute("SELECT COUNT(*) FROM employer_reply_audit WHERE message_id='m1' AND event='RESTORED'").fetchone()[0]==1
    assert not restore_reply(c,'m1')

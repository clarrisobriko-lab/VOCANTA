import sqlite3

from automation.employer_reply_delivery import send_approved_reply
from core.employer_reply_store import approve_reply_draft, save_reply_draft
from intelligence.employer_reply_drafts import build_reply_draft


class Sender:
    def send(self,recipient,subject,body,**kwargs): return 'gmail_sent_123'


def test_gmail_message_identifier_is_persisted_after_send():
    c=sqlite3.connect(':memory:'); draft=build_reply_draft('INTERVIEW','Acme','Counsel','Candidate','Interview'); save_reply_draft(c,'m1',1,draft); approve_reply_draft(c,'m1')
    assert send_approved_reply(c,'m1','talent@acme.com',Sender())
    row=c.execute("SELECT status,gmail_sent_message_id FROM employer_reply_drafts WHERE message_id='m1'").fetchone()
    assert row==('SENT','gmail_sent_123')
    events=c.execute("SELECT event,detail FROM employer_reply_audit WHERE message_id='m1' ORDER BY id").fetchall()
    assert ('GMAIL_ACCEPTED','gmail_sent_123') in events
    assert ('SENT','gmail_sent_123') in events

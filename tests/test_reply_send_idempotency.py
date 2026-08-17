import sqlite3

from automation.employer_reply_delivery import send_approved_reply
from core.employer_reply_store import approve_reply_draft, save_reply_draft
from intelligence.employer_reply_drafts import build_reply_draft


class Sender:
    def __init__(self): self.sent=[]
    def send(self,recipient,subject,body,**kwargs): self.sent.append((recipient,subject,body,kwargs))


def setup_reply():
    c=sqlite3.connect(':memory:')
    c.execute("CREATE TABLE employer_responses(message_id TEXT PRIMARY KEY,sender TEXT,thread_id TEXT,internet_message_id TEXT,references_header TEXT)")
    c.execute("INSERT INTO employer_responses VALUES('m1','talent@acme.com','thread1','<original@acme.com>','')")
    draft=build_reply_draft('INTERVIEW','Acme','Counsel','Candidate','Interview')
    save_reply_draft(c,'m1',1,draft)
    approve_reply_draft(c,'m1')
    return c


def test_same_reply_cannot_send_twice():
    c=setup_reply(); sender=Sender()
    assert send_approved_reply(c,'m1',None,sender)
    assert send_approved_reply(c,'m1',None,sender) is False
    assert len(sender.sent)==1
    assert c.execute("SELECT status FROM employer_reply_drafts WHERE message_id='m1'").fetchone()[0]=='SENT'


def test_duplicate_approval_submission_is_ignored():
    c=setup_reply()
    assert approve_reply_draft(c,'m1') is False
    events=[r[0] for r in c.execute("SELECT event FROM employer_reply_audit WHERE message_id='m1'").fetchall()]
    assert events.count('APPROVED')==1

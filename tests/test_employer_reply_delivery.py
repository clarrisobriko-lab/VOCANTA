import sqlite3

from automation.employer_reply_delivery import send_approved_reply
from core.employer_reply_store import approve_reply_draft, save_reply_draft
from intelligence.employer_reply_drafts import build_reply_draft


class Sender:
    def __init__(self,fail=False): self.fail=fail; self.sent=[]
    def send(self,recipient,subject,body):
        if self.fail: raise RuntimeError('smtp unavailable')
        self.sent.append((recipient,subject,body))


def db(): return sqlite3.connect(':memory:')


def test_unapproved_reply_cannot_send():
    c=db(); draft=build_reply_draft('INTERVIEW','Acme','Counsel','Candidate','Interview'); save_reply_draft(c,'m1',1,draft); sender=Sender()
    assert send_approved_reply(c,'m1','talent@acme.com',sender) is False
    assert sender.sent==[]


def test_approved_reply_sends_and_closes():
    c=db(); draft=build_reply_draft('INTERVIEW','Acme','Counsel','Candidate','Interview'); save_reply_draft(c,'m1',1,draft); approve_reply_draft(c,'m1'); sender=Sender()
    assert send_approved_reply(c,'m1','talent@acme.com',sender)
    assert len(sender.sent)==1
    assert c.execute("SELECT status FROM employer_reply_drafts WHERE message_id='m1'").fetchone()[0]=='SENT'


def test_failed_send_remains_approved_for_retry():
    c=db(); draft=build_reply_draft('OFFER','Acme','Counsel','Candidate','Offer'); save_reply_draft(c,'m1',1,draft); approve_reply_draft(c,'m1')
    assert send_approved_reply(c,'m1','talent@acme.com',Sender(fail=True)) is False
    row=c.execute("SELECT status,last_error FROM employer_reply_drafts WHERE message_id='m1'").fetchone()
    assert row[0]=='APPROVED'
    assert row[1]

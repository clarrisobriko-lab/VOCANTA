import sqlite3

from automation.employer_reply_delivery import send_approved_reply


class Sender:
    def __init__(self): self.calls=[]
    def send(self,recipient,subject,body,**kwargs): self.calls.append((recipient,subject,body,kwargs))


def test_approved_reply_uses_stored_employer_and_thread_context():
    c=sqlite3.connect(':memory:')
    c.execute("CREATE TABLE employer_reply_drafts(message_id TEXT PRIMARY KEY,subject TEXT,body TEXT,status TEXT)")
    c.execute("CREATE TABLE employer_responses(message_id TEXT PRIMARY KEY,sender TEXT,thread_id TEXT,internet_message_id TEXT,references_header TEXT)")
    c.execute("INSERT INTO employer_reply_drafts VALUES('m1','Re: Interview','Thank you','APPROVED')")
    c.execute("INSERT INTO employer_responses VALUES('m1','talent@acme.com','thread1','<original@acme.com>','<earlier@acme.com>')")
    sender=Sender()
    assert send_approved_reply(c,'m1',None,sender)
    call=sender.calls[0]
    assert call[0]=='talent@acme.com'
    assert call[3]['thread_id']=='thread1'
    assert call[3]['in_reply_to']=='<original@acme.com>'
    assert call[3]['references']=='<earlier@acme.com>'

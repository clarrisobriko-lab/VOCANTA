import sqlite3
from types import SimpleNamespace

from automation.response_notification_runtime import notify_processed_responses


class Sender:
    def __init__(self): self.sent=[]
    def send(self,subject,body): self.sent.append((subject,body))


def db():
    c=sqlite3.connect(':memory:')
    c.execute('CREATE TABLE jobs(id INTEGER PRIMARY KEY,company TEXT,title TEXT)')
    c.execute('CREATE TABLE employer_responses(message_id TEXT PRIMARY KEY,job_id INTEGER,classification TEXT,confidence INTEGER,reason TEXT,sender TEXT)')
    c.execute("INSERT INTO jobs VALUES(1,'Acme','Counsel')")
    c.execute("INSERT INTO employer_responses VALUES('m1',1,'OFFER',95,'offer language','talent@acme.com')")
    return c


def test_alert_is_delivered_once():
    c=db(); sender=Sender(); result=SimpleNamespace(status='PROCESSED',job_id=1,message_id='m1')
    assert notify_processed_responses(c,[result],sender)==['m1']
    assert len(sender.sent)==1
    assert notify_processed_responses(c,[result],sender)==[]
    assert len(sender.sent)==1

import sqlite3
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

from automation.response_notification_runtime import notify_processed_responses


class Sender:
    def __init__(self,fail=True): self.fail=fail; self.sent=[]
    def send(self,subject,body):
        if self.fail: raise RuntimeError('temporary smtp failure')
        self.sent.append((subject,body))


def db():
    c=sqlite3.connect(':memory:')
    c.execute('CREATE TABLE jobs(id INTEGER PRIMARY KEY,company TEXT,title TEXT)')
    c.execute('CREATE TABLE employer_responses(message_id TEXT PRIMARY KEY,job_id INTEGER,classification TEXT,confidence INTEGER,reason TEXT,sender TEXT)')
    c.execute("INSERT INTO jobs VALUES(1,'Acme','Counsel')")
    c.execute("INSERT INTO employer_responses VALUES('m1',1,'OFFER',95,'offer language','talent@acme.com')")
    return c


def test_failed_alert_stays_pending_for_retry():
    c=db(); result=SimpleNamespace(status='PROCESSED',job_id=1,message_id='m1')
    assert notify_processed_responses(c,[result],Sender())==[]
    row=c.execute('SELECT status,attempts,next_attempt_at FROM response_notifications WHERE message_id=?',('m1',)).fetchone()
    assert row[0]=='PENDING'
    assert row[1]==1
    assert row[2]


def test_duplicate_ingestion_can_retry_existing_alert():
    c=db(); result=SimpleNamespace(status='PROCESSED',job_id=1,message_id='m1'); notify_processed_responses(c,[result],Sender())
    c.execute("UPDATE response_notifications SET next_attempt_at=? WHERE message_id='m1'",((datetime.now(timezone.utc)-timedelta(minutes=1)).isoformat(),)); c.commit()
    sender=Sender(fail=False); duplicate=SimpleNamespace(status='DUPLICATE',job_id=1,message_id='m1')
    assert notify_processed_responses(c,[duplicate],sender)==['m1']
    assert c.execute("SELECT status FROM response_notifications WHERE message_id='m1'").fetchone()[0]=='DELIVERED'

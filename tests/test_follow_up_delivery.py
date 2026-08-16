from datetime import datetime, timezone
import sqlite3

from automation.follow_up_delivery import process_follow_ups

NOW=datetime(2026,8,16,tzinfo=timezone.utc)


def db():
    c=sqlite3.connect(":memory:"); c.row_factory=sqlite3.Row
    c.execute("CREATE TABLE jobs(id INTEGER PRIMARY KEY,company TEXT,title TEXT,url TEXT,applied INTEGER,status TEXT,applied_date TEXT)")
    c.execute("INSERT INTO jobs VALUES(1,'Acme','Executive Assistant','https://example.com',1,'APPLIED','2026-08-01T00:00:00+00:00')")
    return c


class Sender:
    def __init__(self, fail=False): self.messages=[]; self.fail=fail
    def send(self, recipient, message):
        if self.fail: raise RuntimeError('mail unavailable')
        self.messages.append((recipient,message)); return 'delivery-1'


def test_verified_recipient_is_sent_and_completed():
    c=db(); sender=Sender()
    results=process_follow_ups(c,'Test Candidate',lambda company,url:'jobs@acme.test',sender,now=NOW)
    assert results[0].status=='SENT'
    assert sender.messages[0][0]=='jobs@acme.test'
    assert c.execute("SELECT status FROM application_follow_ups").fetchone()[0]=='COMPLETED'


def test_missing_recipient_is_not_guessed_or_completed():
    c=db(); sender=Sender()
    results=process_follow_ups(c,'Test Candidate',lambda company,url:'',sender,now=NOW)
    assert results[0].status=='NO_RECIPIENT'
    assert sender.messages==[]
    assert c.execute("SELECT status FROM application_follow_ups").fetchone()[0]=='PENDING'


def test_delivery_failure_is_scheduled_for_later_retry():
    c=db(); sender=Sender(fail=True)
    results=process_follow_ups(c,'Test Candidate',lambda company,url:'jobs@acme.test',sender,now=NOW)
    assert results[0].status=='RETRYABLE'
    row=c.execute("SELECT status,attempt_count,next_attempt_at FROM application_follow_ups").fetchone()
    assert row['status']=='PENDING'
    assert row['attempt_count']==1
    assert row['next_attempt_at']

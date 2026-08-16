from datetime import datetime, timedelta, timezone
import sqlite3

from core.follow_up_store import due_follow_ups, follow_up_statistics, generate_follow_up_queue, record_follow_up_failure

NOW=datetime(2026,8,16,tzinfo=timezone.utc)


def db():
    c=sqlite3.connect(':memory:'); c.row_factory=sqlite3.Row
    c.execute("CREATE TABLE jobs(id INTEGER PRIMARY KEY,company TEXT,title TEXT,url TEXT,applied INTEGER,status TEXT,applied_date TEXT)")
    c.execute("INSERT INTO jobs VALUES(1,'Acme','Legal Officer','https://acme.test/job',1,'APPLIED','2026-08-01T00:00:00+00:00')")
    generate_follow_up_queue(c,now=NOW); return c


def test_failure_is_delayed_until_retry_window():
    c=db(); row=due_follow_ups(c,now=NOW)[0]
    assert record_follow_up_failure(c,row['id'],'smtp timeout',now=NOW,retry_minutes=60)
    assert due_follow_ups(c,now=NOW+timedelta(minutes=59))==[]
    assert len(due_follow_ups(c,now=NOW+timedelta(minutes=61)))==1


def test_retry_budget_marks_follow_up_failed():
    c=db(); row=due_follow_ups(c,now=NOW)[0]
    record_follow_up_failure(c,row['id'],'one',now=NOW,max_attempts=2,retry_minutes=0)
    assert record_follow_up_failure(c,row['id'],'two',now=NOW,max_attempts=2,retry_minutes=0) is False
    assert follow_up_statistics(c)['failed']==1
    assert due_follow_ups(c,now=NOW)==[]


def test_statistics_expose_dashboard_states():
    c=db(); stats=follow_up_statistics(c)
    assert stats['pending']==1
    assert stats['completed']==0
    assert stats['failed']==0

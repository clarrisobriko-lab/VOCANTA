from datetime import datetime, timezone
import sqlite3

from core.follow_up_store import complete_follow_up, due_follow_ups, generate_follow_up_queue

NOW=datetime(2026,8,16,tzinfo=timezone.utc)


def db():
    connection=sqlite3.connect(":memory:")
    connection.execute("CREATE TABLE jobs(id INTEGER PRIMARY KEY,company TEXT,title TEXT,url TEXT,applied INTEGER,status TEXT,applied_date TEXT)")
    connection.execute("INSERT INTO jobs VALUES(1,'Acme','Executive Assistant','https://example.com',1,'APPLIED','2026-08-01T00:00:00+00:00')")
    return connection


def test_due_application_generates_follow_up():
    connection=db()
    assert generate_follow_up_queue(connection,now=NOW)==1
    rows=due_follow_ups(connection,now=NOW)
    assert len(rows)==1
    assert rows[0][2]=='FIRST_FOLLOW_UP'


def test_generation_is_idempotent():
    connection=db()
    assert generate_follow_up_queue(connection,now=NOW)==1
    assert generate_follow_up_queue(connection,now=NOW)==0


def test_completed_first_follow_up_allows_second():
    connection=db(); generate_follow_up_queue(connection,now=NOW)
    first=due_follow_ups(connection,now=NOW)[0]
    complete_follow_up(connection,first[0],now=NOW)
    assert generate_follow_up_queue(connection,now=NOW)==1
    pending=due_follow_ups(connection,now=NOW)
    assert pending[0][2]=='SECOND_FOLLOW_UP'


def test_recent_application_not_queued():
    connection=db(); connection.execute("UPDATE jobs SET applied_date='2026-08-14T00:00:00+00:00'")
    assert generate_follow_up_queue(connection,now=NOW)==0

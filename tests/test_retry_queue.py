from datetime import datetime, timedelta, timezone
import sqlite3

from core.retry_queue import clear_retry, due_retries, retire_retry, schedule_retry


def db():
    connection = sqlite3.connect(":memory:")
    connection.execute("CREATE TABLE jobs(id INTEGER PRIMARY KEY, applied INTEGER DEFAULT 0)")
    connection.execute("INSERT INTO jobs(id,applied) VALUES(1,0)")
    return connection


def test_retry_becomes_due_after_cooldown():
    connection=db(); now=datetime(2026,1,1,tzinfo=timezone.utc)
    assert schedule_retry(connection,1,"network",cooldown_seconds=60,now=now)
    assert due_retries(connection,now=now)==[]
    assert due_retries(connection,now=now+timedelta(seconds=61))[0].job_id==1


def test_retry_budget_retires_job():
    connection=db(); now=datetime(2026,1,1,tzinfo=timezone.utc)
    assert schedule_retry(connection,1,"network",now=now,max_attempts=2)
    assert schedule_retry(connection,1,"network",now=now,max_attempts=2) is False
    assert due_retries(connection,now=now+timedelta(hours=1))==[]


def test_clear_retry_removes_successful_job():
    connection=db(); now=datetime(2026,1,1,tzinfo=timezone.utc)
    schedule_retry(connection,1,"network",now=now)
    clear_retry(connection,1)
    assert connection.execute("SELECT COUNT(*) FROM application_retry_queue").fetchone()[0]==0


def test_terminal_retry_is_retired():
    connection=db(); now=datetime(2026,1,1,tzinfo=timezone.utc)
    schedule_retry(connection,1,"network",now=now)
    retire_retry(connection,1,"closed")
    assert due_retries(connection,now=now+timedelta(hours=1))==[]

import sqlite3
from datetime import datetime, timedelta, timezone

from core.employer_reply_store import apply_reply_retention


def test_retention_run_history_is_bounded_and_keeps_newest():
    connection=sqlite3.connect(':memory:')
    start=datetime(2026,8,17,tzinfo=timezone.utc)
    for offset in range(7):
        apply_reply_retention(connection,now=start+timedelta(minutes=offset),history_limit=3)
    rows=connection.execute("SELECT created_at FROM employer_reply_retention_runs ORDER BY id").fetchall()
    assert len(rows)==3
    assert [row[0] for row in rows]==[(start+timedelta(minutes=offset)).isoformat() for offset in range(4,7)]


def test_retention_run_history_enforces_minimum_one_record():
    connection=sqlite3.connect(':memory:')
    start=datetime(2026,8,17,tzinfo=timezone.utc)
    apply_reply_retention(connection,now=start,history_limit=0)
    apply_reply_retention(connection,now=start+timedelta(minutes=1),history_limit=0)
    rows=connection.execute("SELECT created_at FROM employer_reply_retention_runs").fetchall()
    assert rows==[((start+timedelta(minutes=1)).isoformat(),)]

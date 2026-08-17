import sqlite3
from datetime import datetime, timedelta, timezone

from analytics import retention_history, retention_trend
from core.employer_reply_store import ensure_reply_schema


def _seed(connection, values):
    ensure_reply_schema(connection)
    start=datetime(2026,8,17,tzinfo=timezone.utc)
    for offset,(archives,audit) in enumerate(values):
        connection.execute("INSERT INTO employer_reply_retention_runs(archived_replies,audit_events,created_at) VALUES(?,?,?)",(archives,audit,(start+timedelta(minutes=offset)).isoformat()))
    connection.commit()


def test_retention_history_returns_newest_first_with_totals():
    connection=sqlite3.connect(':memory:'); _seed(connection,[(1,2),(3,4),(5,6)])
    history=retention_history(connection,limit=2)
    assert [item['total_removed'] for item in history]==[11,7]


def test_retention_trend_detects_rising_recent_cleanup_volume():
    connection=sqlite3.connect(':memory:'); _seed(connection,[(1,0),(2,0),(3,0),(4,0),(5,0),(20,0),(21,0),(22,0),(23,0),(24,0)])
    trend=retention_trend(connection,limit=10)
    assert trend['runs']==10
    assert trend['latest_removed']==24
    assert trend['peak_removed']==24
    assert trend['direction']=='up'


def test_retention_trend_handles_empty_history():
    connection=sqlite3.connect(':memory:')
    assert retention_trend(connection)=={'runs':0,'total_removed':0,'average_removed':0.0,'peak_removed':0,'latest_removed':0,'direction':'flat'}

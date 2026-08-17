import sqlite3
from datetime import datetime, timedelta, timezone

from core.employer_reply_store import mark_retention_alerted


def test_retention_alert_history_is_bounded():
    connection=sqlite3.connect(':memory:')
    base=datetime(2026,8,17,tzinfo=timezone.utc)
    for index in range(5):
        mark_retention_alerted(connection,{'archived_replies':index,'audit_events':100},now=base+timedelta(minutes=index),history_limit=3)
    rows=connection.execute("SELECT signature FROM employer_reply_retention_alerts ORDER BY alerted_at").fetchall()
    assert [row[0] for row in rows]==['2:100','3:100','4:100']

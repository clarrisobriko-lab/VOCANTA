import sqlite3
from datetime import datetime, timezone

from core.employer_reply_store import apply_reply_retention, latest_reply_retention


def test_retention_run_is_recorded_for_observability():
    connection=sqlite3.connect(':memory:')
    now=datetime(2026,8,17,tzinfo=timezone.utc)
    result=apply_reply_retention(connection,now=now)
    assert result=={'archived_replies':0,'audit_events':0}
    assert latest_reply_retention(connection)=={'archived_replies':0,'audit_events':0,'created_at':now.isoformat()}

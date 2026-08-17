import sqlite3
from datetime import datetime, timedelta, timezone

from core.employer_reply_store import apply_reply_retention, ensure_reply_schema


def test_retention_removes_expired_archives_and_old_unattached_audit_only():
    connection=sqlite3.connect(':memory:'); ensure_reply_schema(connection); now=datetime(2026,8,17,tzinfo=timezone.utc); old=(now-timedelta(days=800)).isoformat(); recent=(now-timedelta(days=10)).isoformat()
    connection.execute("INSERT INTO employer_reply_drafts(message_id,job_id,subject,body,status,created_at,sent_at,archived_at) VALUES('old',1,'s','b','SENT',?,?,?)",(old,old,old))
    connection.execute("INSERT INTO employer_reply_drafts(message_id,job_id,subject,body,status,created_at,sent_at,archived_at) VALUES('kept',1,'s','b','SENT',?,?,?)",(old,old,recent))
    connection.execute("INSERT INTO employer_reply_audit(message_id,event,detail,created_at) VALUES('old','SENT','',?)",(old,))
    connection.execute("INSERT INTO employer_reply_audit(message_id,event,detail,created_at) VALUES('kept','SENT','',?)",(old,))
    connection.execute("INSERT INTO employer_reply_audit(message_id,event,detail,created_at) VALUES('orphan','EVENT','',?)",(old,)); connection.commit()
    result=apply_reply_retention(connection,now=now,audit_days=365,archive_days=730)
    assert result=={'archived_replies':1,'audit_events':1}
    assert connection.execute("SELECT message_id FROM employer_reply_drafts ORDER BY message_id").fetchall()==[('kept',)]
    assert connection.execute("SELECT message_id FROM employer_reply_audit ORDER BY message_id").fetchall()==[('kept',)]


def test_retention_enforces_safe_minimum_window():
    connection=sqlite3.connect(':memory:'); ensure_reply_schema(connection); now=datetime(2026,8,17,tzinfo=timezone.utc); twenty_days=(now-timedelta(days=20)).isoformat()
    connection.execute("INSERT INTO employer_reply_audit(message_id,event,detail,created_at) VALUES('m1','EVENT','',?)",(twenty_days,)); connection.commit()
    result=apply_reply_retention(connection,now=now,audit_days=1,archive_days=1)
    assert result['audit_events']==0
    assert connection.execute("SELECT COUNT(*) FROM employer_reply_audit").fetchone()[0]==1

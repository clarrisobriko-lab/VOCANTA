import sqlite3
from datetime import datetime, timedelta, timezone

from inbox_runtime import run_inbox_runtime
from core.employer_reply_store import ensure_reply_schema


class DatabaseStub:
    def __init__(self,connection): self.connection=connection


def test_inbox_runtime_applies_reply_retention(monkeypatch):
    connection=sqlite3.connect(':memory:')
    ensure_reply_schema(connection)
    old=(datetime.now(timezone.utc)-timedelta(days=800)).isoformat()
    connection.execute("INSERT INTO employer_reply_drafts(message_id,job_id,subject,body,status,created_at,sent_at,archived_at) VALUES('expired',1,'s','b','SENT',?,?,?)",(old,old,old))
    connection.commit()
    monkeypatch.setattr('inbox_runtime.process_inbox_messages',lambda connection,messages: [])
    result=run_inbox_runtime([],database=DatabaseStub(connection))
    assert result==[]
    assert connection.execute("SELECT COUNT(*) FROM employer_reply_drafts WHERE message_id='expired'").fetchone()[0]==0

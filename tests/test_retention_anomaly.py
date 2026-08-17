import sqlite3
from datetime import datetime, timedelta, timezone

from core.employer_reply_store import ensure_reply_schema
from inbox_runtime import retention_anomaly, retention_baseline


def _seed(connection,values):
    ensure_reply_schema(connection); start=datetime(2026,8,17,tzinfo=timezone.utc)
    for offset,value in enumerate(values): connection.execute("INSERT INTO employer_reply_retention_runs(archived_replies,audit_events,created_at) VALUES(?,?,?)",(value,0,(start+timedelta(minutes=offset)).isoformat()))
    connection.commit()


def test_retention_anomaly_detects_spike_against_prior_runs():
    connection=sqlite3.connect(':memory:'); _seed(connection,[10,11,9,10,10,50])
    result=retention_anomaly(connection,{'archived_replies':50,'audit_events':0})
    assert result['runs']==5
    assert result['anomalous'] is True


def test_retention_anomaly_requires_enough_history():
    connection=sqlite3.connect(':memory:'); _seed(connection,[1,1,50])
    assert retention_anomaly(connection,{'archived_replies':50,'audit_events':0})['anomalous'] is False


def test_retention_baseline_excludes_current_run():
    connection=sqlite3.connect(':memory:'); _seed(connection,[10,10,10,10,10,1000])
    baseline=retention_baseline(connection)
    assert baseline['runs']==5
    assert baseline['mean']==10.0
    assert baseline['threshold']==10.0

import sqlite3
from datetime import datetime, timedelta, timezone

from analytics import retention_anomaly_status
from core.employer_reply_store import ensure_reply_schema


def _seed(connection,values):
    ensure_reply_schema(connection); start=datetime(2026,8,17,tzinfo=timezone.utc)
    for offset,value in enumerate(values): connection.execute("INSERT INTO employer_reply_retention_runs(archived_replies,audit_events,created_at) VALUES(?,?,?)",(value,0,(start+timedelta(minutes=offset)).isoformat()))
    connection.commit()


def test_anomaly_status_reports_spike_and_baseline_metrics():
    connection=sqlite3.connect(':memory:'); _seed(connection,[10,11,9,10,10,50])
    result=retention_anomaly_status(connection)
    assert result['status']=='anomaly'
    assert result['anomalous'] is True
    assert result['latest_removed']==50
    assert result['baseline_runs']==5
    assert result['baseline_mean']==10.0


def test_anomaly_status_reports_warming_before_minimum_history():
    connection=sqlite3.connect(':memory:'); _seed(connection,[10,20,30])
    result=retention_anomaly_status(connection)
    assert result['status']=='warming'
    assert result['anomalous'] is False
    assert result['baseline_runs']==2


def test_anomaly_status_reports_unavailable_without_runs():
    connection=sqlite3.connect(':memory:')
    result=retention_anomaly_status(connection)
    assert result['status']=='unavailable'
    assert result['baseline_runs']==0

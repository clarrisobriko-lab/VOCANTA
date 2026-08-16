import sqlite3

from core.outcome_store import ensure_outcome_schema, outcome_statistics, record_outcome
from intelligence.application_outcomes import Outcome


def connection():
    db = sqlite3.connect(":memory:")
    db.execute("CREATE TABLE jobs(id INTEGER PRIMARY KEY, applied INTEGER DEFAULT 0, status TEXT DEFAULT 'NEW', applied_date TEXT, updated_at TEXT)")
    return db


def test_applied_outcome_updates_job_and_history_store():
    db = connection()
    record_outcome(db, 1, Outcome("APPLIED", True, False, False, 100, "submission confirmed"))
    row = db.execute("SELECT applied,status,applied_date FROM jobs WHERE id=1").fetchone()
    assert row[0] == 1
    assert row[1] == "APPLIED"
    assert row[2]
    stored = db.execute("SELECT status,confidence FROM application_outcomes").fetchone()
    assert stored == ("APPLIED", 100)


def test_retry_and_human_states_are_counted():
    db = connection()
    record_outcome(db, 1, Outcome("REQUEUE", False, True, False, 95, "retry"))
    record_outcome(db, 1, Outcome("HUMAN_REQUIRED", False, False, True, 100, "captcha"))
    stats = outcome_statistics(db)
    assert stats["requeue"] == 1
    assert stats["human_required"] == 1
    assert stats["retry_later"] == 1

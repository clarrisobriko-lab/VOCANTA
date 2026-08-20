import sqlite3

from core.submission_audit import list_submission_evidence, record_submission_evidence


def test_submission_evidence_is_queryable_by_job(tmp_path):
    connection = sqlite3.connect(tmp_path / "audit.db")
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    connection.execute("CREATE TABLE jobs(id INTEGER PRIMARY KEY)")
    connection.execute("CREATE TABLE application_runs(id INTEGER PRIMARY KEY)")
    connection.execute("INSERT INTO jobs(id) VALUES(7)")
    connection.execute("INSERT INTO application_runs(id) VALUES(11)")

    evidence_id = record_submission_evidence(
        connection,
        job_id=7,
        application_run_id=11,
        evidence_path="packages/7/submission_evidence/evidence.json",
        package_sha256="a" * 64,
        ats="lever",
        outcome="submitted",
        confirmation_url="https://jobs.lever.co/acme/thanks",
        screenshot_path="screenshots/7.png",
    )
    connection.commit()

    rows = list_submission_evidence(connection, 7)
    assert evidence_id > 0
    assert len(rows) == 1
    assert rows[0]["application_run_id"] == 11
    assert rows[0]["package_sha256"] == "a" * 64
    assert rows[0]["ats"] == "LEVER"
    assert rows[0]["outcome"] == "SUBMITTED"

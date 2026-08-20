import sqlite3
from types import SimpleNamespace

from automation.application_pipeline import _persist_pipeline_evidence
from core.models import Job
from core.submission_audit import list_submission_evidence


def test_pipeline_writes_filesystem_and_database_evidence(tmp_path):
    connection = sqlite3.connect(tmp_path / "vocanta.db")
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    connection.execute("CREATE TABLE jobs(id INTEGER PRIMARY KEY)")
    connection.execute("CREATE TABLE application_runs(id INTEGER PRIMARY KEY)")
    connection.execute("INSERT INTO jobs(id) VALUES(42)")
    connection.execute("INSERT INTO application_runs(id) VALUES(9)")

    folder = tmp_path / "package"
    folder.mkdir()
    cv = folder / "cv.pdf"
    cover = folder / "cover.pdf"
    archive = tmp_path / "package.zip"
    cv.write_bytes(b"cv")
    cover.write_bytes(b"cover")
    archive.write_bytes(b"package")
    package = SimpleNamespace(folder=folder, cv_pdf=cv, cover_letter_pdf=cover, archive=archive)
    automation = SimpleNamespace(status="SUBMITTED", message="received", active_url="https://jobs.lever.co/acme/thanks", screenshot_path="proof.png")
    job = Job(company="Acme", title="Executive Assistant", location="Remote", source="Lever", url="https://jobs.lever.co/acme/123", description="")

    path = _persist_pipeline_evidence(job, 42, package, automation, database=connection, application_run_id=9)
    rows = list_submission_evidence(connection, 42)

    assert path.exists()
    assert len(rows) == 1
    assert rows[0]["application_run_id"] == 9
    assert rows[0]["evidence_path"] == str(path)
    assert rows[0]["outcome"] == "SUBMITTED"
    assert len(rows[0]["package_sha256"]) == 64

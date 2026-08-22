import tempfile
from pathlib import Path

from connectors.registry import get_connectors
from core.database import Database
from core.models import Job


def test_live_registry_contains_promoted_production_connectors():
    assert [connector.name for connector in get_connectors()] == ["Greenhouse", "Lever", "Ashby", "SmartRecruiters", "Workday", "HiddenRoles", "UnlistedRemote", "InclusivelyRemote", "RemoteRocketship", "Remotive", "WorkingNomads", "Jobspresso", "TaskFavour"]


def test_terminal_job_url_is_suppressed_before_rediscovery():
    with tempfile.TemporaryDirectory() as folder:
        database = Database(Path(folder) / "vocanta.db")
        try:
            job = Job(
                company="Canonical",
                title="Executive Assistant",
                location="Remote worldwide",
                source="Greenhouse",
                url="https://boards.greenhouse.io/canonical/jobs/123",
                description="International applicants welcome",
                score=100,
            )
            database.upsert_job(job)
            row = database.connection.execute("SELECT id FROM jobs").fetchone()
            database.record_automation_attempt(row["id"], "MANUAL_REQUIRED", "Own words response required", "")
            reason = database.terminal_automation_reason_for_url(job.url)
            assert reason is not None
            assert "MANUAL_REQUIRED" in reason
        finally:
            database.close()


def test_temporary_failure_remains_retryable():
    with tempfile.TemporaryDirectory() as folder:
        database = Database(Path(folder) / "vocanta.db")
        try:
            job = Job(
                company="Example",
                title="HR Assistant",
                location="Remote worldwide",
                source="Greenhouse",
                url="https://boards.greenhouse.io/example/jobs/456",
                description="International applicants welcome",
                score=100,
            )
            database.upsert_job(job)
            row = database.connection.execute("SELECT id FROM jobs").fetchone()
            database.record_automation_attempt(row["id"], "FAILED", "Temporary timeout", "")
            assert database.terminal_automation_reason_for_url(job.url) is None
        finally:
            database.close()

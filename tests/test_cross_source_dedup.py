import tempfile
from pathlib import Path

from automation.idempotency import canonicalize_job_url
from core.database import Database
from core.models import Job


def test_canonicalizer_removes_common_source_tracking():
    direct = "https://boards.greenhouse.io/acme/jobs/123"
    discovered = "https://www.boards.greenhouse.io/acme/jobs/123/?utm_source=hiddenroles&gh_src=abc&ref=unlistedremote"
    assert canonicalize_job_url(direct) == canonicalize_job_url(discovered)


def test_database_collapses_same_employer_url_across_sources():
    with tempfile.TemporaryDirectory() as folder:
        database = Database(Path(folder) / "vocanta.db")
        try:
            database.upsert_job(Job(
                company="Acme",
                title="Executive Assistant",
                location="Remote",
                source="Greenhouse",
                url="https://jobs.example.com/role/123",
            ))
            database.upsert_job(Job(
                company="jobs.example.com",
                title="Executive Assistant",
                location="Remote",
                source="HiddenRoles",
                url="https://www.jobs.example.com/role/123/?utm_source=hiddenroles&ref=feed",
            ))
            count = database.connection.execute("SELECT COUNT(*) AS n FROM jobs").fetchone()["n"]
            assert count == 1
        finally:
            database.close()


def test_distinct_job_ids_are_not_collapsed():
    first = canonicalize_job_url("https://jobs.lever.co/acme/111?utm_source=hiddenroles")
    second = canonicalize_job_url("https://jobs.lever.co/acme/222?utm_source=unlistedremote")
    assert first != second

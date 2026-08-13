import tempfile
import unittest
import sqlite3
from pathlib import Path

from agents.filters import JobFilter
from agents.scorer import Scorer
from automation.ats import adapter_for_url
from automation.forms import FINAL_SUBMIT_TEXTS, find_action_control
from automation.idempotency import (
    application_idempotency_key,
    canonicalize_job_url,
)
from core.database import Database
from core.models import Job
from intelligence.assessment import assess_job
from intelligence.eligibility import assess_eligibility


def make_job(description: str, location: str = "Remote") -> Job:
    return Job(
        company="Example",
        title="Operations Coordinator",
        location=location,
        source="test",
        url="https://jobs.example.com/roles/42?utm_source=test",
        description=description,
        score=90,
    )


class FakeControl:
    def __init__(self, text: str) -> None:
        self.text = text

    def is_visible(self):
        return True

    def is_enabled(self):
        return True

    def get_attribute(self, _name):
        return None

    def inner_text(self):
        return self.text


class FakeControls:
    def __init__(self, controls) -> None:
        self.controls = controls

    def count(self):
        return len(self.controls)

    def nth(self, index):
        return self.controls[index]


class FakeFrame:
    def __init__(self, text: str) -> None:
        self.control = FakeControl(text)

    def locator(self, _selector):
        return FakeControls([self.control])


class FakePage:
    def __init__(self, text: str) -> None:
        self.main_frame = FakeFrame(text)
        self.frames = [self.main_frame]


class SafetyReleaseTests(unittest.TestCase):
    def test_hard_geography_rules_fail_closed(self):
        for phrase in ("EU only", "UK only", "US only"):
            with self.subTest(phrase=phrase):
                job = make_job(phrase)
                self.assertEqual(assess_eligibility(job).verdict, "BLOCK")
                self.assertEqual(Scorer().score(job), 0)

    def test_negated_geography_does_not_false_block(self):
        decision = assess_eligibility(
            make_job("This role is not US only and welcomes global applicants.")
        )
        self.assertNotEqual(decision.verdict, "BLOCK")

    def test_negative_sponsorship_does_not_match_positive_rule(self):
        decision = assess_eligibility(make_job("No sponsorship available."))
        self.assertEqual(decision.verdict, "BLOCK")
        self.assertNotIn("SPONSORSHIP_AVAILABLE", decision.reason_codes)

    def test_global_remote_does_not_require_relocation_sponsorship(self):
        decision = assess_eligibility(
            make_job("No sponsorship available.", "Global remote")
        )
        self.assertEqual(decision.verdict, "APPLY")

    def test_regional_anywhere_language_does_not_bypass_restrictions(self):
        decision = assess_eligibility(
            make_job(
                "No sponsorship available. Work from anywhere in the EU.",
                "Remote",
            )
        )
        self.assertEqual(decision.verdict, "BLOCK")
        self.assertIn("GEOGRAPHY_RESTRICTED", decision.reason_codes)

    def test_apply_text_is_never_a_final_submit_control(self):
        self.assertNotIn("apply", FINAL_SUBMIT_TEXTS)
        self.assertNotIn("apply now", FINAL_SUBMIT_TEXTS)
        self.assertIsNone(
            find_action_control(
                FakePage("Apply now"),
                ("submit application",),
                exact=True,
            )
        )
        self.assertIsNotNone(
            find_action_control(
                FakePage("Submit application"),
                ("submit application",),
                exact=True,
            )
        )

    def test_only_verified_adapters_allow_auto_submit(self):
        self.assertTrue(
            adapter_for_url("https://boards.greenhouse.io/acme/jobs/1")
            .auto_submit_allowed
        )
        self.assertTrue(
            adapter_for_url("https://jobs.lever.co/acme/1").auto_submit_allowed
        )
        self.assertFalse(
            adapter_for_url("https://example.com/jobs/1").auto_submit_allowed
        )
        self.assertTrue(
            adapter_for_url("https://acme.myworkdayjobs.com/job/1")
            .auto_submit_allowed
        )

    def test_canonical_url_deduplication(self):
        first = canonicalize_job_url(
            "https://Jobs.Example.com/roles/42/?utm_source=one#details"
        )
        second = canonicalize_job_url(
            "https://jobs.example.com/roles/42?utm_source=two"
        )
        self.assertEqual(first, second)
        seen: set[str] = set()
        job_filter = JobFilter()
        self.assertTrue(job_filter.has_unique_url(make_job("Global remote"), seen))
        duplicate = make_job("Global remote")
        duplicate = Job(
            duplicate.company,
            duplicate.title,
            duplicate.location,
            duplicate.source,
            "https://jobs.example.com/roles/42?utm_source=other",
            duplicate.description,
            score=duplicate.score,
        )
        self.assertFalse(job_filter.has_unique_url(duplicate, seen))

    def test_application_run_is_idempotent_and_terminal(self):
        with tempfile.TemporaryDirectory() as directory:
            database = Database(Path(directory) / "vocanta.db")
            try:
                job = make_job("Global remote", "Global remote")
                database.upsert_job(job)
                row = database.connection.execute("SELECT * FROM jobs").fetchone()
                database.upsert_job_intelligence(row["url"], assess_job(job))
                key = application_idempotency_key(job.url, "profile", "documents")
                run, claimed = database.claim_application_run(
                    row["id"], key, "profile", "documents"
                )
                self.assertTrue(claimed)
                self.assertEqual(run["status"], "CREATED")
                for status in (
                    "PREPARING",
                    "FORM_FILLED",
                    "SUBMITTING",
                    "SUBMITTED",
                    "UNKNOWN",
                ):
                    run = database.update_application_run(
                        key,
                        status,
                        active_url="https://jobs.example.com/application/42",
                    )
                self.assertEqual(run["status"], "UNKNOWN")
                self.assertEqual(
                    run["active_url"],
                    "https://jobs.example.com/application/42",
                )
                self.assertEqual(database.list_automation_candidates(85, 10), [])
                existing, claimed_again = database.claim_application_run(
                    row["id"], key, "profile", "documents"
                )
                self.assertFalse(claimed_again)
                self.assertEqual(existing["status"], "UNKNOWN")
            finally:
                database.close()

    def test_invalid_state_transition_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            database = Database(Path(directory) / "vocanta.db")
            try:
                job = make_job("Global remote", "Global remote")
                database.upsert_job(job)
                row = database.connection.execute("SELECT * FROM jobs").fetchone()
                database.claim_application_run(
                    row["id"], "transition-key", "profile", "documents"
                )
                with self.assertRaises(ValueError):
                    database.update_application_run(
                        "transition-key",
                        "CONFIRMED",
                    )
            finally:
                database.close()

    def test_v25_schema_migrates_to_v261(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "legacy.db"
            connection = sqlite3.connect(path)
            connection.executescript(
                """
                CREATE TABLE jobs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    company TEXT NOT NULL,
                    title TEXT NOT NULL,
                    location TEXT NOT NULL DEFAULT '',
                    source TEXT NOT NULL,
                    url TEXT NOT NULL UNIQUE,
                    description TEXT NOT NULL DEFAULT '',
                    salary TEXT NOT NULL DEFAULT '',
                    employment_type TEXT NOT NULL DEFAULT '',
                    score INTEGER NOT NULL DEFAULT 0,
                    status TEXT NOT NULL DEFAULT 'NEW',
                    applied INTEGER NOT NULL DEFAULT 0,
                    applied_date TEXT,
                    follow_up_date TEXT,
                    notes TEXT NOT NULL DEFAULT '',
                    first_seen_at TEXT NOT NULL,
                    last_seen_at TEXT NOT NULL,
                    updated_at TEXT
                );
                CREATE TABLE job_intelligence (
                    job_url TEXT PRIMARY KEY,
                    sponsorship_score INTEGER NOT NULL DEFAULT 0,
                    sponsorship_label TEXT NOT NULL DEFAULT 'UNKNOWN',
                    relocation_label TEXT NOT NULL DEFAULT 'UNKNOWN',
                    international_hiring_label TEXT NOT NULL DEFAULT 'UNKNOWN',
                    confidence INTEGER NOT NULL DEFAULT 0,
                    ngo_label TEXT NOT NULL DEFAULT 'CORPORATE',
                    blocked INTEGER NOT NULL DEFAULT 0,
                    block_reason TEXT NOT NULL DEFAULT '',
                    block_category TEXT NOT NULL DEFAULT '',
                    recommendation TEXT NOT NULL DEFAULT 'APPLY',
                    assessed_at TEXT NOT NULL
                );
                INSERT INTO jobs(
                    company, title, location, source, url,
                    first_seen_at, last_seen_at
                ) VALUES(
                    'Example', 'Operations Manager', 'Remote', 'test',
                    'https://example.com/job?utm_source=old',
                    '2026-01-01T00:00:00+00:00',
                    '2026-01-01T00:00:00+00:00'
                );
                """
            )
            connection.close()

            database = Database(path)
            try:
                job_columns = {
                    row["name"]
                    for row in database.connection.execute(
                        "PRAGMA table_info(jobs)"
                    )
                }
                intelligence_columns = {
                    row["name"]
                    for row in database.connection.execute(
                        "PRAGMA table_info(job_intelligence)"
                    )
                }
                self.assertIn("canonical_url", job_columns)
                self.assertIn("decision_verdict", intelligence_columns)
                version = database.connection.execute(
                    "SELECT value FROM schema_metadata "
                    "WHERE key = 'schema_version'"
                ).fetchone()["value"]
                self.assertEqual(version, "2.6.1")
            finally:
                database.close()

    def test_notification_delivery_is_deduplicated(self):
        with tempfile.TemporaryDirectory() as directory:
            database = Database(Path(directory) / "vocanta.db")
            try:
                job = make_job("Global remote", "Global remote")
                database.upsert_job(job)
                row = database.connection.execute("SELECT * FROM jobs").fetchone()
                delivery, claimed = database.claim_notification_delivery(
                    row["id"],
                    "notification-key",
                    "OAUTH",
                )
                self.assertTrue(claimed)
                self.assertEqual(delivery["status"], "QUEUED")
                database.update_notification_delivery(
                    "notification-key",
                    "SENDING",
                )
                sent = database.update_notification_delivery(
                    "notification-key",
                    "SENT",
                )
                self.assertEqual(sent["attempt_count"], 1)
                existing, claimed_again = database.claim_notification_delivery(
                    row["id"],
                    "notification-key",
                    "OAUTH",
                )
                self.assertFalse(claimed_again)
                self.assertEqual(existing["status"], "SENT")
                with self.assertRaises(ValueError):
                    database.update_notification_delivery(
                        "notification-key",
                        "OUTBOX",
                    )
            finally:
                database.close()

    def test_v260_application_run_adds_active_url(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "v260.db"
            connection = sqlite3.connect(path)
            connection.executescript(
                """
                CREATE TABLE jobs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    company TEXT NOT NULL,
                    title TEXT NOT NULL,
                    location TEXT NOT NULL DEFAULT '',
                    source TEXT NOT NULL,
                    url TEXT NOT NULL UNIQUE,
                    canonical_url TEXT NOT NULL DEFAULT '',
                    description TEXT NOT NULL DEFAULT '',
                    salary TEXT NOT NULL DEFAULT '',
                    employment_type TEXT NOT NULL DEFAULT '',
                    score INTEGER NOT NULL DEFAULT 0,
                    status TEXT NOT NULL DEFAULT 'NEW',
                    applied INTEGER NOT NULL DEFAULT 0,
                    applied_date TEXT,
                    follow_up_date TEXT,
                    notes TEXT NOT NULL DEFAULT '',
                    first_seen_at TEXT NOT NULL,
                    last_seen_at TEXT NOT NULL,
                    updated_at TEXT
                );
                CREATE TABLE application_runs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    job_id INTEGER NOT NULL,
                    idempotency_key TEXT NOT NULL UNIQUE,
                    candidate_profile_hash TEXT NOT NULL,
                    document_hash TEXT NOT NULL,
                    status TEXT NOT NULL,
                    started_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    completed_at TEXT,
                    confirmation_text TEXT NOT NULL DEFAULT '',
                    confirmation_url TEXT NOT NULL DEFAULT '',
                    screenshot_path TEXT NOT NULL DEFAULT '',
                    last_error TEXT NOT NULL DEFAULT '',
                    FOREIGN KEY(job_id) REFERENCES jobs(id) ON DELETE CASCADE
                );
                """
            )
            connection.close()

            database = Database(path)
            try:
                run_columns = {
                    row["name"]
                    for row in database.connection.execute(
                        "PRAGMA table_info(application_runs)"
                    )
                }
                self.assertIn("active_url", run_columns)
            finally:
                database.close()


if __name__ == "__main__":
    unittest.main()

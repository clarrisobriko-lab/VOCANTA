import tempfile
import unittest
from pathlib import Path

from connectors.registry import get_connectors
from core.database import Database
from core.models import Job
from core.revalidation import revalidate_existing_jobs
from intelligence.eligibility import assess_eligibility, blocked_automation_domain


class V294ProductionTests(unittest.TestCase):
    def test_remoteok_connector_is_fully_disabled(self):
        names = {connector.name.lower() for connector in get_connectors()}
        self.assertNotIn("remoteok", names)

    def test_cloudflare_prone_marketplaces_are_hard_blocked(self):
        self.assertEqual(blocked_automation_domain("https://remoteok.com/jobs/1"), "remoteok.com")
        self.assertEqual(blocked_automation_domain("https://jobgether.com/job/1"), "jobgether.com")
        self.assertEqual(blocked_automation_domain("https://himalayas.app/jobs/1"), "himalayas.app")

    def test_beijing_office_job_is_blocked(self):
        job = Job(
            company="Canonical",
            title="Beijing Office Administrator",
            location="Office Based - Beijing, China",
            source="Greenhouse",
            url="https://boards.greenhouse.io/canonical/jobs/1",
            description="Canonical is a global company.",
            score=100,
        )
        decision = assess_eligibility(job)
        self.assertEqual(decision.verdict, "BLOCK")

    def test_revalidation_closes_stale_human_queue_for_rejected_job(self):
        with tempfile.TemporaryDirectory() as folder:
            database = Database(Path(folder) / "vocanta.db")
            try:
                job = Job(
                    company="Canonical",
                    title="Beijing Office Administrator",
                    location="Office Based - Beijing, China",
                    source="Greenhouse",
                    url="https://boards.greenhouse.io/canonical/jobs/2",
                    description="Global company",
                    score=100,
                )
                database.upsert_job(job)
                database.connection.commit()
                row = database.connection.execute("SELECT id FROM jobs").fetchone()
                database.queue_human_action(row["id"], "READY_TO_REVIEW", "old", 100, 100)
                revalidate_existing_jobs(database)
                queue = database.connection.execute(
                    "SELECT resolved_at FROM human_action_queue WHERE job_id = ?", (row["id"],)
                ).fetchone()
                self.assertIsNotNone(queue["resolved_at"])
            finally:
                database.close()


if __name__ == "__main__":
    unittest.main()

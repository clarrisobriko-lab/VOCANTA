import tempfile
import unittest
from pathlib import Path

from core.database import Database
from core.models import Job
from core.revalidation import revalidate_existing_jobs
from intelligence.eligibility import assess_eligibility, production_block_reason


class V295ProductionTests(unittest.TestCase):
    def test_ireland_without_explicit_international_eligibility_is_blocked(self):
        job = Job(company="Example", title="Executive Assistant", location="Dublin, Ireland", source="Greenhouse", url="https://boards.greenhouse.io/example/jobs/1", description="Office role for local candidates.")
        self.assertIsNotNone(production_block_reason(job))

    def test_ireland_with_sponsorship_is_priority(self):
        job = Job(company="Example", title="Executive Assistant", location="Dublin, Ireland", source="Greenhouse", url="https://boards.greenhouse.io/example/jobs/2", description="Visa sponsorship available for international candidates.")
        self.assertIsNone(production_block_reason(job))

    def test_worldwide_remote_is_allowed(self):
        job = Job(company="Example", title="Administrative Assistant", location="Remote worldwide", source="Greenhouse", url="https://boards.greenhouse.io/example/jobs/3", description="Work from anywhere in the world.")
        self.assertIsNone(production_block_reason(job))

    def test_emea_only_is_blocked(self):
        job = Job(company="Example", title="HR Assistant", location="Remote, EMEA", source="Greenhouse", url="https://boards.greenhouse.io/example/jobs/4", description="Remote across EMEA.")
        self.assertIsNotNone(production_block_reason(job))

    def test_migrated_ineligible_job_is_purged(self):
        with tempfile.TemporaryDirectory() as folder:
            db = Database(Path(folder) / "vocanta.db")
            try:
                db.upsert_job(Job(company="Canonical", title="Beijing Office Administrator", location="Beijing, China", source="Greenhouse", url="https://boards.greenhouse.io/canonical/jobs/99", description="Office based"))
                revalidate_existing_jobs(db)
                self.assertEqual(db.connection.execute("SELECT COUNT(*) FROM jobs").fetchone()[0], 0)
            finally:
                db.close()


if __name__ == "__main__":
    unittest.main()

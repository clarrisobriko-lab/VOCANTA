import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

from core.database import Database
from core.models import Job


class V299FollowUpGuardTests(unittest.TestCase):
    def _job(self, db: Database, suffix: str) -> int:
        job = Job(
            company="Canonical",
            title="Executive Assistant / Corporate Administrator",
            location="Home based - EMEA",
            source="Greenhouse",
            url=f"https://boards.greenhouse.io/canonical/jobs/{suffix}",
            description="Home based role open across EMEA.",
            score=100,
        )
        db.upsert_job(job)
        db.connection.commit()
        return int(db.connection.execute("SELECT id FROM jobs WHERE url=?", (job.url,)).fetchone()[0])

    def test_stale_history_does_not_preserve_false_follow_up(self):
        with tempfile.TemporaryDirectory() as folder:
            db = Database(Path(folder) / "vocanta.db")
            try:
                job_id = self._job(db, "history")
                now = datetime.now(timezone.utc).isoformat()
                db.connection.execute("UPDATE jobs SET status='FOLLOW_UP', applied=1 WHERE id=?", (job_id,))
                db.connection.execute(
                    "INSERT INTO application_history(job_id, old_status, new_status, notes, changed_at) VALUES(?, 'APPLIED', 'FOLLOW_UP', 'legacy false positive', ?)",
                    (job_id, now),
                )
                db.connection.commit()

                repaired = db.repair_job_statuses("TEST_HISTORY")
                self.assertEqual(len(repaired), 1)
                self.assertEqual(db.get_job(job_id)["status"], "NEW")
            finally:
                db.close()

    def test_follow_up_cannot_be_set_without_submission(self):
        with tempfile.TemporaryDirectory() as folder:
            db = Database(Path(folder) / "vocanta.db")
            try:
                job_id = self._job(db, "guard")
                with self.assertRaisesRegex(ValueError, "FOLLOW_UP requires"):
                    db.update_application(job_id, "FOLLOW_UP")
                self.assertEqual(db.get_job(job_id)["status"], "NEW")
            finally:
                db.close()

    def test_prequeue_build_repairs_false_follow_up(self):
        with tempfile.TemporaryDirectory() as folder:
            db = Database(Path(folder) / "vocanta.db")
            try:
                job_id = self._job(db, "prequeue")
                now = datetime.now(timezone.utc).isoformat()
                db.connection.execute("UPDATE jobs SET status='FOLLOW_UP' WHERE id=?", (job_id,))
                db.connection.execute(
                    """
                    INSERT INTO job_intelligence(
                        job_url, sponsorship_score, sponsorship_label,
                        relocation_label, international_hiring_label, confidence,
                        ngo_label, blocked, block_reason, block_category,
                        recommendation, decision_verdict, decision_reason_codes,
                        decision_evidence, rule_version, primary_reason, assessed_at
                    ) VALUES(?, 0, 'UNKNOWN', 'UNKNOWN', 'YES', 95,
                             'CORPORATE', 0, '', '', 'APPLY', 'APPLY', '', '',
                             'v2.9.9', 'International eligibility detected', ?)
                    """,
                    ("https://boards.greenhouse.io/canonical/jobs/prequeue", now),
                )
                db.connection.commit()

                candidates = db.list_automation_candidates(70, 10)
                self.assertEqual(len(candidates), 1)
                self.assertEqual(candidates[0]["id"], job_id)
                self.assertEqual(db.get_job(job_id)["status"], "NEW")
            finally:
                db.close()


if __name__ == "__main__":
    unittest.main()

import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

from core.database import Database
from core.models import Job


class V298StatusRepairTests(unittest.TestCase):
    def _job(self, db: Database, suffix: str = "1") -> int:
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

    def test_unsubmitted_follow_up_is_repaired_to_new(self):
        with tempfile.TemporaryDirectory() as folder:
            db = Database(Path(folder) / "vocanta.db")
            try:
                job_id = self._job(db)
                now = datetime.now(timezone.utc).isoformat()
                db.connection.execute(
                    "UPDATE jobs SET status='FOLLOW_UP', applied=1, applied_date=?, follow_up_date=? WHERE id=?",
                    (now, now, job_id),
                )
                db.connection.execute(
                    """
                    INSERT INTO application_runs(
                        job_id, idempotency_key, candidate_profile_hash,
                        document_hash, status, started_at, updated_at
                    ) VALUES(?, 'review-only', 'profile', 'docs',
                             'HUMAN_VERIFICATION', ?, ?)
                    """,
                    (job_id, now, now),
                )
                db.connection.commit()

                repaired = db.repair_job_statuses("TEST")
                self.assertEqual(len(repaired), 1)
                row = db.get_job(job_id)
                self.assertEqual(row["status"], "NEW")
                self.assertEqual(row["applied"], 0)
                self.assertIsNone(row["applied_date"])
                audit = db.connection.execute(
                    "SELECT previous_status, new_status, stage FROM job_status_audit WHERE job_id=?",
                    (job_id,),
                ).fetchone()
                self.assertEqual(tuple(audit), ("FOLLOW_UP", "NEW", "TEST"))
            finally:
                db.close()

    def test_confirmed_submission_preserves_follow_up(self):
        with tempfile.TemporaryDirectory() as folder:
            db = Database(Path(folder) / "vocanta.db")
            try:
                job_id = self._job(db, "2")
                now = datetime.now(timezone.utc).isoformat()
                db.connection.execute(
                    "UPDATE jobs SET status='FOLLOW_UP', applied=1, applied_date=? WHERE id=?",
                    (now, job_id),
                )
                db.connection.execute(
                    """
                    INSERT INTO application_runs(
                        job_id, idempotency_key, candidate_profile_hash,
                        document_hash, status, started_at, updated_at
                    ) VALUES(?, 'submitted', 'profile', 'docs',
                             'SUBMITTED', ?, ?)
                    """,
                    (job_id, now, now),
                )
                db.connection.commit()

                repaired = db.repair_job_statuses("TEST")
                self.assertEqual(repaired, [])
                self.assertEqual(db.get_job(job_id)["status"], "FOLLOW_UP")
            finally:
                db.close()

    def test_repaired_job_can_enter_automation_queue(self):
        with tempfile.TemporaryDirectory() as folder:
            db = Database(Path(folder) / "vocanta.db")
            try:
                job_id = self._job(db, "3")
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
                    ("https://boards.greenhouse.io/canonical/jobs/3", now),
                )
                db.connection.commit()
                db.repair_job_statuses("TEST")
                self.assertEqual(db.automation_queue_count(70), 1)
                self.assertEqual(db.list_automation_candidates(70, 10)[0]["id"], job_id)
            finally:
                db.close()


if __name__ == "__main__":
    unittest.main()

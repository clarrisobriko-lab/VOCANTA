import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

from core.database import Database
from core.models import Job


class V297QueueConsistencyTests(unittest.TestCase):
    def _create_queueable_job(self, db: Database) -> int:
        job = Job(
            company="Example",
            title="Executive Assistant",
            location="Remote worldwide",
            source="Greenhouse",
            url="https://boards.greenhouse.io/example/jobs/297",
            description="Work from anywhere in the world.",
            score=100,
        )
        db.upsert_job(job)
        now = datetime.now(timezone.utc).isoformat()
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
                     'v2.9.7', 'Worldwide remote role', ?)
            """,
            (job.url, now),
        )
        db.connection.commit()
        return int(db.connection.execute("SELECT id FROM jobs WHERE url=?", (job.url,)).fetchone()[0])

    def test_dashboard_apply_count_matches_queue(self):
        with tempfile.TemporaryDirectory() as folder:
            db = Database(Path(folder) / "vocanta.db")
            try:
                self._create_queueable_job(db)
                self.assertEqual(db.automation_queue_count(70), 1)
                self.assertEqual(db.mission_briefing(60)["apply_jobs"], 1)
                self.assertEqual(db.list_jobs(60)[0]["recommendation"], "APPLY")
            finally:
                db.close()

    def test_existing_application_run_is_not_silently_shown_as_apply(self):
        with tempfile.TemporaryDirectory() as folder:
            db = Database(Path(folder) / "vocanta.db")
            try:
                job_id = self._create_queueable_job(db)
                now = datetime.now(timezone.utc).isoformat()
                db.connection.execute(
                    """
                    INSERT INTO application_runs(
                        job_id, idempotency_key, candidate_profile_hash,
                        document_hash, status, started_at, updated_at
                    ) VALUES(?, 'existing-run', 'profile', 'documents',
                             'CREATED', ?, ?)
                    """,
                    (job_id, now, now),
                )
                db.connection.commit()
                self.assertEqual(db.automation_queue_count(70), 0)
                self.assertEqual(db.mission_briefing(60)["apply_jobs"], 0)
                self.assertEqual(db.list_jobs(60)[0]["recommendation"], "NOT_QUEUED")
                diagnostics = db.automation_queue_diagnostics(70)
                self.assertEqual(diagnostics[0]["reason"], "Application run already exists")
            finally:
                db.close()

    def test_every_queue_entry_has_unique_audit_id(self):
        with tempfile.TemporaryDirectory() as folder:
            db = Database(Path(folder) / "vocanta.db")
            try:
                self._create_queueable_job(db)
                candidates = db.list_automation_candidates(70, 10)
                self.assertEqual(len(candidates), 1)
                queue_id = candidates[0]["queue_id"]
                audit = db.connection.execute(
                    "SELECT decision, reason FROM automation_queue_audit WHERE queue_id=?",
                    (queue_id,),
                ).fetchone()
                self.assertIsNotNone(audit)
                self.assertEqual(audit["decision"], "ACCEPTED")
                self.assertEqual(audit["reason"], "Eligible for automation")
            finally:
                db.close()


if __name__ == "__main__":
    unittest.main()

import tempfile
import unittest
from pathlib import Path

from agents.scorer import ApplicationDecision
from automation.acquisition_audit import AcquisitionAuditStore
from core.database import Database
from core.models import Job


class AcquisitionAuditTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.database = Database(Path(self.temp.name) / "vocanta.db")
        self.job = Job("Example", "Executive Assistant", "Remote", "Test", "https://example.test/audit")
        self.database.upsert_jobs([self.job])
        self.job_id = int(self.database.connection.execute("SELECT id FROM jobs WHERE url = ?", (self.job.url,)).fetchone()["id"])
        self.store = AcquisitionAuditStore(self.database)

    def tearDown(self):
        self.database.close()
        self.temp.cleanup()

    def test_decision_round_trips_with_skills_and_reason(self):
        decision = ApplicationDecision(78, 82, 71, True, ("executive support", "scheduling"), ("salesforce",), "Eligible for automatic application")
        audit_id = self.store.record(self.job_id, decision)
        saved = self.store.latest(self.job_id)
        self.assertGreater(audit_id, 0)
        self.assertEqual(saved["composite_score"], 78)
        self.assertEqual(saved["ats_score"], 71)
        self.assertTrue(saved["should_apply"])
        self.assertEqual(saved["matched_skills"], ("executive support", "scheduling"))
        self.assertEqual(saved["missing_skills"], ("salesforce",))
        self.assertEqual(saved["reason"], "Eligible for automatic application")

    def test_history_preserves_changed_decisions(self):
        first = ApplicationDecision(55, 70, 30, False, ("scheduling",), ("salesforce", "workday"), "ATS coverage 30% is below 50% minimum")
        second = ApplicationDecision(74, 78, 67, True, ("scheduling", "executive support"), ("salesforce",), "Eligible for automatic application")
        self.store.record(self.job_id, first)
        self.store.record(self.job_id, second)
        history = self.store.history(self.job_id)
        self.assertEqual(len(history), 2)
        self.assertTrue(history[0]["should_apply"])
        self.assertFalse(history[1]["should_apply"])

    def test_unknown_job_is_rejected(self):
        decision = ApplicationDecision(80, 80, 80, True, (), (), "Eligible for automatic application")
        with self.assertRaises(ValueError):
            self.store.record(999999, decision)


if __name__ == "__main__":
    unittest.main()

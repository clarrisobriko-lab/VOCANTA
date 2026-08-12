import unittest
from agents.matcher import Matcher
from agents.scorer import Scorer
from core.models import Job


class ScoringTests(unittest.TestCase):
    def setUp(self):
        self.matcher = Matcher()
        self.scorer = Scorer()

    def test_hr_role_is_relevant(self):
        job = Job("Example", "HR Business Partner", "Remote, United Kingdom", "Test", "https://example.test/1", description="Recruitment onboarding employee relations and personnel records")
        self.assertTrue(self.matcher.is_relevant(job))
        self.assertGreaterEqual(self.scorer.score(job), 60)
        decision = self.scorer.evaluate(job)
        self.assertTrue(decision.should_apply)
        self.assertEqual(decision.ats_score, 100)

    def test_engineering_role_is_rejected(self):
        job = Job("Example", "Software Engineer", "Remote", "Test", "https://example.test/2")
        self.assertFalse(self.matcher.is_relevant(job))
        self.assertEqual(self.scorer.score(job), 0)
        self.assertFalse(self.scorer.evaluate(job).should_apply)

    def test_material_ats_gap_blocks_auto_apply(self):
        job = Job("Example", "Executive Assistant", "Remote", "Test", "https://example.test/3", description="Salesforce CRM and Workday HCM required")
        decision = self.scorer.evaluate(job)
        self.assertFalse(decision.should_apply)
        self.assertLess(decision.ats_score, self.scorer.MIN_ATS_COVERAGE)
        self.assertIn("salesforce", decision.missing_skills)
        self.assertIn("workday", decision.missing_skills)
        self.assertIn("below", decision.reason.lower())

    def test_verified_strengths_can_outweigh_tolerable_gap(self):
        job = Job("Example", "Executive Assistant", "Remote", "Test", "https://example.test/4", description="Executive diaries, leadership meetings, scheduling and Salesforce CRM")
        decision = self.scorer.evaluate(job)
        self.assertGreaterEqual(decision.ats_score, self.scorer.MIN_ATS_COVERAGE)
        self.assertIn("salesforce", decision.missing_skills)
        if decision.score >= self.scorer.AUTO_APPLY_THRESHOLD:
            self.assertTrue(decision.should_apply)


if __name__ == "__main__":
    unittest.main()

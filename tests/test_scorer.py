import unittest
from agents.matcher import Matcher
from agents.scorer import Scorer
from core.models import Job


class ScoringTests(unittest.TestCase):
    def setUp(self):
        self.matcher = Matcher()
        self.scorer = Scorer()

    def test_hr_role_is_relevant(self):
        job = Job("Example", "HR Business Partner", "Remote, United Kingdom", "Test", "https://example.test/1")
        self.assertTrue(self.matcher.is_relevant(job))
        self.assertGreaterEqual(self.scorer.score(job), 60)

    def test_engineering_role_is_rejected(self):
        job = Job("Example", "Software Engineer", "Remote", "Test", "https://example.test/2")
        self.assertFalse(self.matcher.is_relevant(job))
        self.assertEqual(self.scorer.score(job), 0)


if __name__ == "__main__":
    unittest.main()

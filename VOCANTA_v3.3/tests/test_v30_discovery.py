import unittest

from core.discovery import DiscoveryEngine, RejectionReason
from core.models import Job


class StubFilter:
    def has_unique_url(self, job, seen_urls):
        if job.url in seen_urls:
            return False
        seen_urls.add(job.url)
        return True

    def has_supported_location(self, job):
        return job.location != "Blocked"


class StubMatcher:
    def is_relevant(self, job):
        return "Engineer" not in job.title


class StubScorer:
    def score(self, job):
        return 80 if "Assistant" in job.title else 20


class DiscoveryEngineTests(unittest.TestCase):
    def setUp(self):
        self.engine = DiscoveryEngine(35, StubFilter(), StubMatcher(), StubScorer())
        self.seen = set()

    def job(self, **overrides):
        values = {
            "company": "Example",
            "title": "Executive Assistant",
            "location": "Worldwide",
            "source": "Test",
            "url": "https://example.com/jobs/1",
        }
        values.update(overrides)
        return Job(**values)

    def test_accepts_valid_relevant_job(self):
        result = self.engine.evaluate(self.job(), self.seen)
        self.assertTrue(result.accepted)
        self.assertEqual(result.job.score, 80)
        self.assertIsNotNone(result.intelligence)

    def test_rejects_engineering_job_before_scoring(self):
        result = self.engine.evaluate(self.job(title="Software Engineer"), self.seen)
        self.assertEqual(result.rejection_reason, RejectionReason.ROLE)

    def test_rejects_duplicate_canonical_url(self):
        first = self.engine.evaluate(self.job(), self.seen)
        second = self.engine.evaluate(self.job(), self.seen)
        self.assertTrue(first.accepted)
        self.assertEqual(second.rejection_reason, RejectionReason.DUPLICATE)

    def test_rejects_incomplete_job(self):
        result = self.engine.evaluate(self.job(company=""), self.seen)
        self.assertEqual(result.rejection_reason, RejectionReason.INVALID)

    def test_rejects_below_threshold(self):
        result = self.engine.evaluate(self.job(title="Legal Coordinator"), self.seen)
        self.assertEqual(result.rejection_reason, RejectionReason.SCORE)


class JobModelTests(unittest.TestCase):
    def test_normalizes_and_clamps_input(self):
        job = Job(" Company ", " Role ", None, " Source ", " https://x ", score=120)
        self.assertEqual(job.company, "Company")
        self.assertEqual(job.location, "")
        self.assertEqual(job.score, 100)
        self.assertTrue(job.is_valid)

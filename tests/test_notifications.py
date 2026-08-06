import tempfile
import unittest
from pathlib import Path

from core.models import Job
from intelligence.assessment import assess_job
from intelligence.opportunity import assess_opportunity


class NotificationTests(unittest.TestCase):
    def test_high_value_blocked_application_is_selected(self):
        job = Job(
            company="Example",
            title="Operations Coordinator",
            location="United Kingdom",
            source="test",
            url="https://example.com/job",
            description=(
                "Visa sponsorship available. Relocation support. "
                "Private medical insurance and professional development."
            ),
            score=92,
        )
        intelligence = assess_job(job)
        opportunity = assess_opportunity(job, intelligence, 92, 88)
        self.assertTrue(opportunity.high_value)
        self.assertGreaterEqual(opportunity.score, 92)

    def test_low_score_unknown_role_is_not_high_value(self):
        job = Job(
            company="Example",
            title="Executive Assistant",
            location="Remote",
            source="test",
            url="https://example.com/job2",
            description="Standard administrative support.",
            score=70,
        )
        intelligence = assess_job(job)
        opportunity = assess_opportunity(job, intelligence, 92, 88)
        self.assertFalse(opportunity.high_value)


if __name__ == "__main__":
    unittest.main()

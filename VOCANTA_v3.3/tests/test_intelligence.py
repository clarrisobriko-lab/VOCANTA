import unittest

from core.models import Job
from intelligence.assessment import assess_job
from intelligence.ngo import assess_ngo
from intelligence.restrictions import assess_restrictions
from intelligence.sponsorship import assess_sponsorship


def make_job(
    company: str = "Example",
    location: str = "United Kingdom",
    description: str = "",
) -> Job:
    return Job(
        company=company,
        title="Executive Assistant",
        location=location,
        source="test",
        url="https://example.com/job",
        description=description,
    )


class IntelligenceTests(unittest.TestCase):
    def test_venezuela_only_is_blocked(self):
        result = assess_restrictions(
            make_job(location="Remote", description="Venezuela only")
        )
        self.assertTrue(result.blocked)
        self.assertEqual(result.category, "GEOGRAPHY")

    def test_sponsorship_positive(self):
        result = assess_sponsorship(
            make_job(description="Visa sponsorship available and relocation support.")
        )
        self.assertEqual(result.label, "YES")
        self.assertEqual(result.relocation, "YES")

    def test_no_sponsorship(self):
        result = assess_sponsorship(
            make_job(description="No visa sponsorship is available.")
        )
        self.assertEqual(result.label, "NO")

    def test_ngo_priority(self):
        result = assess_ngo(
            make_job(company="Save the Children", description="Humanitarian programme")
        )
        self.assertEqual(result.label, "NGO_PRIORITY")

    def test_priority_recommendation(self):
        result = assess_job(
            make_job(description="International applicants encouraged. Visa sponsorship available.")
        )
        self.assertEqual(result.recommendation, "PRIORITY")


if __name__ == "__main__":
    unittest.main()

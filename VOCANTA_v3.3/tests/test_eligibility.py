import unittest

from agents.eligibility import assess_eligibility
from core.models import Job


def make_job(
    description: str = "",
    company: str = "Example Company",
    location: str = "United Kingdom",
) -> Job:
    return Job(
        company=company,
        title="Human Resources Assistant",
        location=location,
        source="test",
        url="https://example.com/job",
        description=description,
    )


class EligibilityTests(unittest.TestCase):
    def test_positive_sponsorship(self):
        result = assess_eligibility(
            make_job("Visa sponsorship and relocation support available.")
        )
        self.assertEqual(result.sponsorship, "YES")
        self.assertEqual(result.relocation, "YES")
        self.assertEqual(result.verdict, "PRIORITY")

    def test_negative_sponsorship(self):
        result = assess_eligibility(
            make_job("No visa sponsorship is available.")
        )
        self.assertEqual(result.sponsorship, "NO")
        self.assertEqual(result.verdict, "IGNORE")

    def test_ngo_priority(self):
        result = assess_eligibility(
            make_job(company="Save the Children")
        )
        self.assertEqual(result.organisation, "NGO")
        self.assertEqual(result.verdict, "RESEARCH")

    def test_unknown_sponsorship_requires_review(self):
        result = assess_eligibility(make_job())
        self.assertEqual(result.sponsorship, "UNKNOWN")
        self.assertEqual(result.verdict, "RESEARCH")


if __name__ == "__main__":
    unittest.main()

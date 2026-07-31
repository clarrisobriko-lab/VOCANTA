import unittest

from agents.scorer import Scorer
from core.models import Job
from intelligence.eligibility import assess_eligibility, required_experience_years


class V27GuardrailTests(unittest.TestCase):
    def test_us_only_is_blocked(self):
        job = Job(
            company="James River Group",
            title="Manager, Regulatory Compliance",
            location="United States only",
            source="Himalayas",
            url="https://example.com/us-only",
            description="Senior role. 5 years minimum.",
        )
        decision = assess_eligibility(job)
        self.assertTrue(decision.blocked)
        self.assertIn("GEOGRAPHY_RESTRICTED", decision.reason_codes)
        self.assertEqual(Scorer().score(job), 0)

    def test_five_year_requirement_is_blocked(self):
        job = Job(
            company="Example",
            title="Compliance Manager",
            location="Remote worldwide",
            source="test",
            url="https://example.com/five-years",
            description="Applicants need a minimum of 5 years of experience.",
        )
        decision = assess_eligibility(job)
        self.assertTrue(decision.blocked)
        self.assertIn("EXPERIENCE_TOO_HIGH", decision.reason_codes)

    def test_entry_global_remote_is_prioritised(self):
        job = Job(
            company="Global NGO",
            title="HR Assistant",
            location="Remote worldwide",
            source="test",
            url="https://example.com/hr-assistant",
            description="Open to candidates worldwide. English working language.",
        )
        decision = assess_eligibility(job)
        self.assertFalse(decision.blocked)
        self.assertEqual(decision.career_level, "ENTRY")
        self.assertGreaterEqual(Scorer().score(job), 60)

    def test_regional_remote_without_openness_is_blocked(self):
        job = Job(
            company="Example",
            title="Executive Assistant",
            location="Remote, USA",
            source="test",
            url="https://example.com/remote-usa",
            description="Remote role for US candidates.",
        )
        self.assertTrue(assess_eligibility(job).blocked)

    def test_year_parser(self):
        self.assertEqual(required_experience_years("5 years minimum"), 5)
        self.assertEqual(required_experience_years("2-3 years experience"), 2)


if __name__ == '__main__':
    unittest.main()

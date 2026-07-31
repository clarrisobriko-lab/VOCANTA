import unittest

from agents.market_intelligence import assess_market
from agents.scorer import Scorer
from core.models import Job


def make_job(location: str, description: str = "") -> Job:
    return Job(
        company="Example NGO",
        title="Human Resources Assistant",
        location=location,
        source="test",
        url=f"https://example.com/{location}",
        description=description,
    )


class MarketIntelligenceTests(unittest.TestCase):
    def test_exact_country_priorities(self):
        expected = {
            "United Kingdom": 100,
            "Ireland": 98,
            "Portugal": 90,
            "Estonia": 85,
            "Lithuania": 84,
            "Latvia": 82,
        }
        for location, score in expected.items():
            with self.subTest(location=location):
                self.assertEqual(assess_market(make_job(location)).market_score, score)

    def test_exact_language_penalties(self):
        expected = {
            "Germany": -20,
            "Austria": -20,
            "France": -25,
            "Spain": -15,
        }
        for location, penalty in expected.items():
            with self.subTest(location=location):
                self.assertEqual(
                    assess_market(make_job(location)).language_penalty,
                    penalty,
                )

    def test_english_exemption_removes_language_penalty(self):
        assessment = assess_market(
            make_job("Germany", "English is the working language.")
        )
        self.assertEqual(assessment.language_penalty, 0)

    def test_global_remote_has_top_market_score(self):
        assessment = assess_market(make_job("Remote worldwide"))
        self.assertEqual(assessment.market_score, 100)

    def test_unsupported_country_is_rejected(self):
        assessment = assess_market(make_job("Venezuela"))
        self.assertFalse(assessment.supported)

    def test_beijing_office_role_is_not_misclassified_as_global_remote(self):
        assessment = assess_market(
            make_job(
                "Office Based - Beijing, China",
                "Canonical is a global company with distributed collaboration worldwide.",
            )
        )
        self.assertFalse(assessment.supported)
        self.assertFalse(assessment.global_remote)

    def test_ireland_role_remains_supported(self):
        assessment = assess_market(make_job("Dublin, Ireland"))
        self.assertTrue(assessment.supported)
        self.assertEqual(assessment.country, "ireland")

    def test_bare_global_company_language_is_not_worldwide_eligibility(self):
        assessment = assess_market(
            make_job("Beijing, China", "We are a global technology company.")
        )
        self.assertFalse(assessment.supported)
        self.assertFalse(assessment.global_remote)

    def test_priority_country_outranks_secondary_country(self):
        scorer = Scorer()
        uk_score = scorer.score(make_job("United Kingdom"))
        germany_score = scorer.score(make_job("Germany"))
        self.assertGreater(uk_score, germany_score)


if __name__ == "__main__":
    unittest.main()

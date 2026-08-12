import unittest

from automation.ats import adapter_for_url
from automation.preflight import assess_application_url
from connectors.registry import get_connectors


class AshbyProductionTests(unittest.TestCase):
    def test_ashby_adapter_is_auto_submit_capable(self):
        adapter = adapter_for_url("https://jobs.ashbyhq.com/example/abc123")
        self.assertEqual(adapter.name, "ASHBY")
        self.assertTrue(adapter.auto_submit_allowed)
        self.assertIn("submit application", adapter.final_submit_texts)
        self.assertIn("application received", adapter.confirmation_phrases)

    def test_ashby_url_passes_preflight(self):
        decision = assess_application_url("https://jobs.ashbyhq.com/example/abc123")
        self.assertTrue(decision.allowed)
        self.assertEqual(decision.ats, "ASHBY")

    def test_ashby_connector_is_in_production_registry(self):
        names = [connector.name for connector in get_connectors()]
        self.assertEqual(names, ["Greenhouse", "Lever", "Ashby"])

    def test_unpromoted_ats_stays_blocked(self):
        for url, expected in (
            ("https://jobs.smartrecruiters.com/example/abc123", "SMARTRECRUITERS"),
            ("https://example.wd5.myworkdayjobs.com/job/abc123", "WORKDAY"),
        ):
            decision = assess_application_url(url)
            self.assertFalse(decision.allowed)
            self.assertEqual(decision.ats, expected)

    def test_generic_form_stays_blocked(self):
        decision = assess_application_url("https://careers.example.com/jobs/abc123")
        self.assertFalse(decision.allowed)
        self.assertEqual(decision.ats, "GENERIC")


if __name__ == "__main__":
    unittest.main()

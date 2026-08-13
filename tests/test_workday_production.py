import unittest

from automation.ats import adapter_for_url
from automation.preflight import assess_application_url
from connectors.registry import get_connectors


class WorkdayProductionTests(unittest.TestCase):
    def test_workday_adapter_is_auto_submit_capable(self):
        adapter = adapter_for_url("https://example.wd5.myworkdayjobs.com/External/job/123")
        self.assertEqual(adapter.name, "WORKDAY")
        self.assertTrue(adapter.auto_submit_allowed)
        self.assertIn("submit", adapter.final_submit_texts)
        self.assertIn("your application has been submitted", adapter.confirmation_phrases)

    def test_workday_url_passes_preflight(self):
        decision = assess_application_url("https://example.wd5.myworkdayjobs.com/External/job/123")
        self.assertTrue(decision.allowed)
        self.assertEqual(decision.ats, "WORKDAY")

    def test_workday_connector_is_in_production_registry(self):
        self.assertEqual(
            [connector.name for connector in get_connectors()],
            ["Greenhouse", "Lever", "Ashby", "SmartRecruiters", "Workday"],
        )

    def test_generic_form_remains_blocked(self):
        decision = assess_application_url("https://careers.example.com/jobs/abc123")
        self.assertFalse(decision.allowed)
        self.assertEqual(decision.ats, "GENERIC")


if __name__ == "__main__":
    unittest.main()

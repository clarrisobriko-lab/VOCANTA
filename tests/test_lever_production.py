import unittest

from automation.ats import adapter_for_url
from automation.preflight import assess_application_url
from connectors.registry import get_connectors


class LeverProductionTests(unittest.TestCase):
    def test_lever_adapter_is_auto_submit_capable(self):
        adapter = adapter_for_url("https://jobs.lever.co/example/abc123")
        self.assertEqual(adapter.name, "LEVER")
        self.assertTrue(adapter.auto_submit_allowed)

    def test_lever_url_passes_preflight(self):
        decision = assess_application_url("https://jobs.lever.co/example/abc123")
        self.assertTrue(decision.allowed)
        self.assertEqual(decision.ats, "LEVER")

    def test_lever_connector_is_in_production_registry(self):
        names = {connector.name for connector in get_connectors()}
        self.assertIn("Lever", names)
        self.assertIn("Greenhouse", names)
        self.assertIn("Ashby", names)
        self.assertIn("SmartRecruiters", names)

    def test_workday_stays_blocked(self):
        decision = assess_application_url("https://example.wd5.myworkdayjobs.com/job/abc123")
        self.assertFalse(decision.allowed)
        self.assertEqual(decision.ats, "WORKDAY")

    def test_generic_form_stays_blocked(self):
        decision = assess_application_url("https://careers.example.com/jobs/abc123")
        self.assertFalse(decision.allowed)
        self.assertEqual(decision.ats, "GENERIC")


if __name__ == "__main__":
    unittest.main()

import unittest

from automation.browser import _blocked_domain
from connectors.registry import get_connectors
from core.models import Job
from intelligence.eligibility import assess_eligibility


class CloudflareRemovalTests(unittest.TestCase):
    def test_himalayas_connector_is_disabled(self):
        names = {connector.name.lower() for connector in get_connectors()}
        self.assertNotIn("himalayas", names)

    def test_himalayas_url_is_blocked(self):
        self.assertEqual(_blocked_domain("https://himalayas.app/jobs/1"), "himalayas.app")

    def test_himalayas_job_is_rejected_before_scoring(self):
        job = Job(
            company="Example",
            title="Administrative Assistant",
            location="Remote worldwide",
            source="Himalayas",
            url="https://himalayas.app/companies/example/jobs/admin",
            description="International applicants welcome",
            score=100,
        )
        decision = assess_eligibility(job)
        self.assertEqual(decision.verdict, "BLOCK")
        self.assertIn("anti-bot verification", decision.primary_reason)


if __name__ == "__main__":
    unittest.main()

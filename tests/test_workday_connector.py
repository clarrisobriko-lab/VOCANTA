import unittest
from unittest.mock import patch

from connectors.workday import WorkdayConnector


class WorkdayConnectorTests(unittest.TestCase):
    def test_name(self):
        self.assertEqual(WorkdayConnector().name, "Workday")

    @patch("connectors.workday.WORKDAY_SITES", {"Example": "https://example.wd5.myworkdayjobs.com/External"})
    @patch("connectors.workday.create_session")
    @patch("connectors.workday.get_json")
    def test_fetch_jobs_normalizes_public_postings(self, get_json, create_session):
        get_json.return_value = {
            "jobPostings": [
                {
                    "title": "Executive Assistant",
                    "locationsText": "Remote",
                    "externalPath": "/job/Executive-Assistant_R123",
                }
            ]
        }
        jobs = list(WorkdayConnector().fetch_jobs())
        self.assertEqual(len(jobs), 1)
        self.assertEqual(jobs[0].company, "Example")
        self.assertEqual(jobs[0].title, "Executive Assistant")
        self.assertEqual(jobs[0].location, "Remote")
        self.assertEqual(jobs[0].source, "Workday")
        self.assertEqual(jobs[0].url, "https://example.wd5.myworkdayjobs.com/External/job/Executive-Assistant_R123")

    @patch("connectors.workday.WORKDAY_SITES", {"Example": "https://example.wd5.myworkdayjobs.com/External"})
    @patch("connectors.workday.create_session")
    @patch("connectors.workday.get_json", side_effect=RuntimeError("blocked"))
    def test_fetch_failure_isolated(self, get_json, create_session):
        self.assertEqual(list(WorkdayConnector().fetch_jobs()), [])


if __name__ == "__main__":
    unittest.main()

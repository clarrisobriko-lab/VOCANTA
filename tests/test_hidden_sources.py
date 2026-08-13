import unittest
from unittest.mock import patch

from connectors.hidden_sources import HiddenRolesConnector, UnlistedRemoteConnector


class _Response:
    def __init__(self, text):
        self.text = text

    def raise_for_status(self):
        return None


class _Session:
    def __init__(self, text):
        self.text = text

    def get(self, url, timeout):
        return _Response(self.text)


class HiddenSourceTests(unittest.TestCase):
    def test_source_names(self):
        self.assertEqual(HiddenRolesConnector().name, "HiddenRoles")
        self.assertEqual(UnlistedRemoteConnector().name, "UnlistedRemote")

    @patch("connectors.hidden_sources.create_session")
    def test_extracts_only_external_public_links(self, create_session):
        create_session.return_value = _Session(
            '<a href="/pricing">Pricing</a>'
            '<a href="https://boards.greenhouse.io/acme/jobs/123">Executive Assistant Remote</a>'
        )
        jobs = list(HiddenRolesConnector().fetch_jobs())
        self.assertEqual(len(jobs), 1)
        self.assertEqual(jobs[0].source, "HiddenRoles")
        self.assertEqual(jobs[0].title, "Executive Assistant Remote")
        self.assertEqual(jobs[0].location, "Remote")
        self.assertEqual(jobs[0].url, "https://boards.greenhouse.io/acme/jobs/123")

    @patch("connectors.hidden_sources.create_session", side_effect=RuntimeError("unavailable"))
    def test_failure_isolated(self, create_session):
        self.assertEqual(list(UnlistedRemoteConnector().fetch_jobs()), [])


if __name__ == "__main__":
    unittest.main()

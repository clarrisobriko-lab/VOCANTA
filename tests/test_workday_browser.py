import unittest

from automation.workday import detect_workday_gate, is_workday_url


class _Body:
    def __init__(self, text):
        self.text = text

    def inner_text(self):
        return self.text


class _Page:
    def __init__(self, url, text=""):
        self.url = url
        self.text = text

    def locator(self, selector):
        assert selector == "body"
        return _Body(self.text)


class WorkdayBrowserGateTests(unittest.TestCase):
    def test_recognizes_workday_hosts(self):
        self.assertTrue(is_workday_url("https://example.wd5.myworkdayjobs.com/External/job/123"))
        self.assertTrue(is_workday_url("https://example.workday.com/login"))
        self.assertFalse(is_workday_url("https://jobs.example.com/job/123"))

    def test_detects_account_creation_gate(self):
        gate = detect_workday_gate(_Page(
            "https://example.wd5.myworkdayjobs.com/External/apply",
            "Already have an account? Sign In. Create an Account",
        ))
        self.assertTrue(gate.blocked)
        self.assertIn("account gate", gate.reason.lower())

    def test_detects_candidate_home_route(self):
        gate = detect_workday_gate(_Page(
            "https://example.wd5.myworkdayjobs.com/External/candidateHome",
            "",
        ))
        self.assertTrue(gate.blocked)
        self.assertIn("account route", gate.reason.lower())

    def test_normal_application_page_is_not_blocked(self):
        gate = detect_workday_gate(_Page(
            "https://example.wd5.myworkdayjobs.com/External/job/123",
            "Executive Assistant Apply Now Resume Email",
        ))
        self.assertFalse(gate.blocked)

    def test_non_workday_page_is_not_blocked(self):
        gate = detect_workday_gate(_Page("https://jobs.example.com/job/123", "Create account"))
        self.assertFalse(gate.blocked)


if __name__ == "__main__":
    unittest.main()

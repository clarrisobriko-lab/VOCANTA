import unittest

from automation.ats_match import analyse_ats_match
from core.models import Job


class ATSMatchTests(unittest.TestCase):
    def test_full_verified_match_scores_100(self):
        job = Job(
            "Example", "HR Manager", "Remote", "test", "https://example.com",
            description="Talent acquisition, new hire orientation, workplace relations and personnel records",
        )
        result = analyse_ats_match(job)
        self.assertEqual(result.score, 100)
        self.assertIn("recruitment", result.matched_skills)
        self.assertIn("onboarding", result.matched_skills)
        self.assertIn("employee relations", result.matched_skills)
        self.assertFalse(result.missing_skills)

    def test_unsupported_tool_is_reported_as_gap(self):
        job = Job(
            "Example", "Executive Assistant", "Remote", "test", "https://example.com",
            description="Manage executive diaries, leadership meetings and Slack collaboration",
        )
        result = analyse_ats_match(job)
        self.assertIn("executive support", result.matched_skills)
        self.assertIn("calendar management", result.matched_skills)
        self.assertIn("scheduling", result.matched_skills)
        self.assertIn("slack", result.missing_skills)
        self.assertLess(result.score, 100)

    def test_no_detected_requirements_is_neutral_not_failure(self):
        job = Job("Example", "Coordinator", "Remote", "test", "https://example.com", description="Support the team")
        result = analyse_ats_match(job)
        self.assertEqual(result.score, 100)
        self.assertEqual(result.required_skills, ())


if __name__ == "__main__":
    unittest.main()

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from agents.scorer import ApplicationDecision
from automation.application_pipeline import profile_for_package, run_application_pipeline
from automation.browser import AutomationResult
from automation.package_builder import ApplicationPackage
from automation.profile import ApplicantProfile
from core.models import Job


class FakeScorer:
    def __init__(self, decision): self.decision = decision
    def evaluate(self, job): return self.decision


class FakeBrowser:
    received_profile = None
    def __init__(self, profile):
        FakeBrowser.received_profile = profile
    def apply(self, url, job_id):
        return AutomationResult("AUTO_SUBMITTED", "confirmed", "", 5, confirmation_url=url)


def profile():
    return ApplicantProfile("Test", "", "User", "test@example.com", "+234000", "Abuja", "Nigeria", "Address", "900001", "", "", "", True, "Immediate", "")


class ApplicationPipelineTests(unittest.TestCase):
    def test_profile_handoff_uses_employer_pdf_files_only(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            cv = root / "cv.pdf"; cover = root / "cover.pdf"; manifest = root / "INTERNAL.json"; archive = root / "package.zip"
            for item in (cv, cover, manifest, archive): item.write_bytes(b"x")
            package = ApplicationPackage(root, cv, cover, (), manifest, archive)
            result = profile_for_package(profile(), package)
            self.assertEqual(result.resume_path, str(cv))
            self.assertEqual(result.cover_letter_path, str(cover))
            self.assertNotIn("INTERNAL", result.resume_path)
            self.assertNotIn("INTERNAL", result.cover_letter_path)

    def test_ineligible_job_never_launches_browser(self):
        decision = ApplicationDecision(20, 30, 10, False, (), ("salesforce",), "Below threshold")
        job = Job("Example", "Executive Assistant", "Remote", "test", "https://example.test/job")
        result = run_application_pipeline(job, 1, profile(), scorer=FakeScorer(decision), browser_engine_factory=FakeBrowser)
        self.assertIsNone(result.documents)
        self.assertIsNone(result.package)
        self.assertIsNone(result.automation)

    def test_eligible_job_hands_package_to_browser(self):
        decision = ApplicationDecision(90, 90, 90, True, ("executive support",), (), "Eligible")
        job = Job("Example", "Executive Assistant", "Remote", "test", "https://example.test/job")
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            cv = root / "cv.pdf"; cover = root / "cover.pdf"; manifest = root / "INTERNAL.json"; archive = root / "package.zip"
            for item in (cv, cover, manifest, archive): item.write_bytes(b"x")
            package = ApplicationPackage(root, cv, cover, (), manifest, archive)
            with patch("automation.application_pipeline.tailor_documents", return_value=object()), patch("automation.application_pipeline.build_application_package", return_value=package):
                result = run_application_pipeline(job, 7, profile(), scorer=FakeScorer(decision), browser_engine_factory=FakeBrowser)
            self.assertEqual(result.automation.status, "AUTO_SUBMITTED")
            self.assertEqual(FakeBrowser.received_profile.resume_path, str(cv))
            self.assertEqual(FakeBrowser.received_profile.cover_letter_path, str(cover))


if __name__ == "__main__":
    unittest.main()

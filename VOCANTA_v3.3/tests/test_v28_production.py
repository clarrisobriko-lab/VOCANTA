import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from agents.scorer import Scorer
from automation.profile import load_profile
from core.models import Job
from intelligence.eligibility import assess_eligibility


class V28ProductionTests(unittest.TestCase):
    def test_manager_title_is_blocked(self):
        job = Job(
            company="Example",
            title="Manager, Regulatory Compliance",
            location="Worldwide",
            source="test",
            url="https://example.com/1",
            description="Remote worldwide.",
        )
        decision = assess_eligibility(job)
        self.assertTrue(decision.blocked)
        self.assertEqual(Scorer().score(job), 0)

    def test_three_year_entry_role_is_eligible(self):
        job = Job(
            company="Example",
            title="Administrative Assistant",
            location="Worldwide",
            source="test",
            url="https://example.com/2",
            description=(
                "Remote worldwide. International candidates welcome. "
                "Three years of administrative experience."
            ),
        )
        decision = assess_eligibility(job)
        self.assertIn(decision.verdict, {"APPLY", "PRIORITY"})
        self.assertGreaterEqual(Scorer().score(job), 70)

    def test_four_year_requirement_is_blocked(self):
        job = Job(
            company="Example",
            title="Operations Coordinator",
            location="Worldwide",
            source="test",
            url="https://example.com/3",
            description="Remote worldwide. Minimum 4 years of experience.",
        )
        self.assertTrue(assess_eligibility(job).blocked)

    def test_old_document_paths_are_repaired(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            profile_file = root / "applicant_profile.json"
            cv = root / "master_cv.docx"
            cover = root / "master_cover_letter.docx"
            cert = root / "certificate.pdf"
            cv.write_bytes(b"cv")
            cover.write_bytes(b"cover")
            cert.write_bytes(b"cert")
            profile_file.write_text(
                """{
                  "first_name": "Clarris",
                  "middle_name": "Phegor",
                  "last_name": "Obriko",
                  "email": "Clarrisobriko@gmail.com",
                  "phone": "+2348055632432",
                  "city": "Abuja",
                  "country": "Nigeria",
                  "address": "",
                  "postal_code": "",
                  "linkedin_url": "",
                  "website_url": "",
                  "work_authorization": "Sponsorship required",
                  "requires_sponsorship": true,
                  "notice_period": "Immediately available",
                  "salary_expectation": "",
                  "resume_path": "C:/missing/old_cv.docx",
                  "cover_letter_path": "C:/missing/old_cover.docx",
                  "supporting_document_path": "C:/missing/old_cert.pdf"
                }""",
                encoding="utf-8",
            )
            with patch("automation.profile.ensure_persistent_assets"), patch(
                "automation.profile.MASTER_CV_FILE", cv
            ), patch(
                "automation.profile.MASTER_COVER_LETTER_FILE", cover
            ), patch(
                "automation.profile.EXECUTIVE_ASSISTANT_CERTIFICATE_FILE", cert
            ):
                profile = load_profile(profile_file)
            self.assertEqual(Path(profile.resume_path), cv)
            self.assertEqual(Path(profile.cover_letter_path), cover)
            self.assertEqual(Path(profile.supporting_document_path), cert)


if __name__ == "__main__":
    unittest.main()

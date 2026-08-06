import tempfile
import unittest
from pathlib import Path

from automation.profile import ApplicantProfile
from automation.tailoring import classify_job, extract_keywords, tailor_documents
from core.models import Job


class TailoringTests(unittest.TestCase):
    def profile(self, root: Path) -> ApplicantProfile:
        resume = root / "master.docx"
        cover = root / "cover.docx"
        cert = root / "cert.pdf"
        resume.write_bytes(b"docx")
        cover.write_bytes(b"docx")
        cert.write_bytes(b"pdf")
        return ApplicantProfile(
            first_name="Alex", middle_name="Morgan", last_name="Taylor",
            email="alex@example.com", phone="+000000000000",
            city="Abuja", country="Nigeria", address="", postal_code="",
            linkedin_url="", website_url="",
            work_authorization="Requires sponsorship",
            requires_sponsorship=True, notice_period="Immediate",
            salary_expectation="", resume_path=str(resume),
            cover_letter_path=str(cover), supporting_document_path=str(cert),
        )

    def test_category_detection(self):
        job = Job("Example", "Executive Assistant", "Remote", "test", "https://example.com")
        self.assertEqual(classify_job(job), "EXECUTIVE_OPERATIONS")

    def test_keyword_extraction(self):
        job = Job("Example", "Operations Coordinator", "Remote", "test", "https://example.com", description="Calendar management and stakeholder management")
        self.assertIn("calendar management", extract_keywords(job))

    def test_documents_are_created(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            profile = self.profile(root)
            job = Job("Example", "Executive Assistant", "Remote", "test", "https://example.com", description="Executive support and scheduling")
            import automation.tailoring as module
            old = module.TAILORED_APPLICATIONS_DIR
            module.TAILORED_APPLICATIONS_DIR = root / "out"
            try:
                docs = tailor_documents(job, 1, profile)
                self.assertTrue(docs.resume_path.is_file())
                self.assertTrue(docs.cover_letter_path.is_file())
                self.assertTrue(docs.certificate_path.is_file())
            finally:
                module.TAILORED_APPLICATIONS_DIR = old


if __name__ == "__main__":
    unittest.main()

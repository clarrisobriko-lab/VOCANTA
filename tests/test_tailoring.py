import tempfile
import unittest
from pathlib import Path

from docx import Document

from automation.profile import ApplicantProfile
from automation.tailoring import (
    CATEGORY_HEADLINES,
    classify_job,
    extract_keywords,
    prioritize_experience,
    tailor_documents,
)
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

    def test_semantic_keyword_synonyms_are_normalised(self):
        cases = (
            ("Manage complex executive diaries and coordinate senior leadership meetings", ("executive support", "calendar management", "scheduling")),
            ("Own talent acquisition, new hire orientation and workplace relations", ("recruitment", "onboarding", "employee relations")),
            ("Perform contract review, regulatory compliance and legal analysis", ("contract management", "compliance", "legal research")),
            ("Prepare management reports using Microsoft 365 and G Suite", ("reporting", "microsoft office", "google workspace")),
        )
        for description, expected in cases:
            with self.subTest(description=description):
                job = Job("Example", "Specialist", "Remote", "test", "https://example.com", description=description)
                matches = extract_keywords(job)
                for keyword in expected:
                    self.assertIn(keyword, matches)

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

    def test_cv_headline_matches_job_category(self):
        cases = (
            ("Executive Assistant", "Executive support and scheduling", "EXECUTIVE_OPERATIONS"),
            ("Human Resources Manager", "Recruitment, onboarding and employee relations", "HR_PEOPLE"),
            ("Legal Counsel", "Legal research, contracts and compliance", "LEGAL_COMPLIANCE"),
            ("Programme Officer", "Humanitarian nonprofit programme coordination", "NGO_PROGRAMME"),
        )
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            profile = self.profile(root)
            import automation.tailoring as module
            old = module.TAILORED_APPLICATIONS_DIR
            module.TAILORED_APPLICATIONS_DIR = root / "out"
            try:
                for job_id, (title, description, expected_category) in enumerate(cases, start=1):
                    with self.subTest(category=expected_category):
                        job = Job("Example", title, "Remote", "test", "https://example.com", description=description)
                        docs = tailor_documents(job, job_id, profile)
                        self.assertEqual(docs.category, expected_category)
                        document = Document(docs.resume_path)
                        text = "\n".join(paragraph.text for paragraph in document.paragraphs)
                        self.assertIn(CATEGORY_HEADLINES[expected_category], text)
            finally:
                module.TAILORED_APPLICATIONS_DIR = old

    def test_experience_is_prioritized_by_category(self):
        expectations = {
            "HR_PEOPLE": "Human Resource Manager",
            "LEGAL_COMPLIANCE": "Legal",
            "NGO_PROGRAMME": "Legal Officer",
            "EXECUTIVE_OPERATIONS": "HR Personnel",
        }
        for category, expected_title_fragment in expectations.items():
            with self.subTest(category=category):
                ranked = prioritize_experience(category)
                self.assertIn(expected_title_fragment, ranked[0][0])


if __name__ == "__main__":
    unittest.main()

import tempfile
import unittest
from pathlib import Path

from automation.forms import identify_field, profile_value
from automation.profile import ApplicantProfile


def make_profile(resume_path: str) -> ApplicantProfile:
    return ApplicantProfile(
        first_name="Alex",
        middle_name="Morgan",
        last_name="Taylor",
        email="alex@example.com",
        phone="+2348000000000",
        city="Abuja",
        country="Nigeria",
        address="",
        postal_code="",
        linkedin_url="",
        website_url="",
        resume_path=resume_path,
        cover_letter_path="",
        supporting_document_path="",
        work_authorization="Requires sponsorship",
        requires_sponsorship=True,
        notice_period="Immediate",
        salary_expectation="",
    )


class AutomationTests(unittest.TestCase):
    def test_field_identification(self):
        self.assertEqual(identify_field("First name"), "first_name")
        self.assertEqual(identify_field("Middle Name"), "middle_name")
        self.assertEqual(identify_field("Email address"), "email")
        self.assertEqual(identify_field("LinkedIn Profile"), "linkedin_url")
        self.assertEqual(identify_field("Desired salary"), "salary_expectation")

    def test_profile_name_rules(self):
        profile = make_profile(__file__)
        self.assertEqual(profile.full_name, "Alex Morgan Taylor")
        self.assertEqual(profile.employer_last_name, "Morgan Taylor")
        self.assertEqual(
            profile_value(profile, "last_name", has_middle_name_field=False),
            "Morgan Taylor",
        )
        self.assertEqual(
            profile_value(profile, "last_name", has_middle_name_field=True),
            "Taylor",
        )
        self.assertEqual(
            profile_value(profile, "middle_name", has_middle_name_field=True),
            "Morgan",
        )

    def test_profile_validation(self):
        with tempfile.TemporaryDirectory() as directory:
            resume = Path(directory) / "cv.pdf"
            resume.write_bytes(b"pdf")
            profile = make_profile(str(resume))
            self.assertEqual(profile.validate(), [])


if __name__ == "__main__":
    unittest.main()

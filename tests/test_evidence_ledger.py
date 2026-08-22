from automation.evidence_ledger import build_evidence_ledger, claim_supported
from automation.profile import ApplicantProfile, EducationRecord, EmploymentRecord


def profile():
    return ApplicantProfile(first_name="Test",middle_name="",last_name="Candidate",email="test@example.com",phone="",city="Abuja",country="Nigeria",address="Abuja, Nigeria",postal_code="",linkedin_url="",website_url="",work_authorization="",requires_sponsorship=True,notice_period="Immediately",salary_expectation="7",nationality="Nigerian",number_of_employers="1",highest_education=EducationRecord("University","LLB","Law","2020","Nigeria"),employment_history=(EmploymentRecord("Human Resources Manager","Company","2024","",True,"Recruitment, onboarding, employee records and staff training."),),resume_path="",cover_letter_path="",supporting_document_path="")


def test_ledger_contains_only_profile_evidence():
    ledger = build_evidence_ledger(profile())
    text = " ".join(item.claim for item in ledger)
    assert "Human Resources Manager" in text
    assert "LLB" in text
    assert "Salesforce" not in text


def test_supported_claim_passes():
    assert claim_supported("Recruitment, onboarding, employee records and staff training.", profile())


def test_unsupported_claim_fails():
    assert not claim_supported("Managed Salesforce CRM for five years", profile())

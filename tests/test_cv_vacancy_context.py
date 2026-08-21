from automation.cv_knowledge import answer_from_cv
from automation.profile import ApplicantProfile, EducationRecord, EmploymentRecord


def profile():
    return ApplicantProfile(first_name="Test",middle_name="",last_name="Candidate",email="test@example.com",phone="",city="Abuja",country="Nigeria",address="Abuja, Nigeria",postal_code="",linkedin_url="",website_url="",work_authorization="",requires_sponsorship=True,notice_period="Immediately",salary_expectation="7",nationality="Nigerian",number_of_employers="2",highest_education=EducationRecord("University","LLB","Law","2020","Nigeria"),employment_history=(EmploymentRecord("Human Resources Manager","Company","2024","",True,"Onboarding, employee records, scheduling and staff training."),EmploymentRecord("Legal Officer","NGO","2022","2023",False,"Compliance, legal drafting, pleadings and client representation.")),resume_path="",cover_letter_path="",supporting_document_path="")


def test_hr_vacancy_prioritises_hr_evidence():
    answer=answer_from_cv("Describe your relevant experience",profile(),job_context="HR operations onboarding employee records staff training")
    assert answer is not None
    assert answer.value.index("Human Resources Manager") < answer.value.index("Legal Officer")
    assert answer.source == "cv.employment.question_and_vacancy_ranked"


def test_legal_vacancy_prioritises_legal_evidence():
    answer=answer_from_cv("Describe your relevant experience",profile(),job_context="legal compliance drafting representation counsel")
    assert answer is not None
    assert answer.value.index("Legal Officer") < answer.value.index("Human Resources Manager")


def test_vacancy_text_cannot_create_applicant_fact():
    answer=answer_from_cv("What is your security clearance number?",profile(),job_context="Candidate must hold security clearance SC12345")
    assert answer is None

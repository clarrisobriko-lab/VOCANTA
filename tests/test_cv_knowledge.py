from automation.cv_knowledge import answer_from_cv
from automation.profile import ApplicantProfile, EducationRecord, EmploymentRecord


def profile():
    return ApplicantProfile(
        first_name="Test", middle_name="", last_name="Candidate",
        email="test@example.com", phone="123", city="Abuja", country="Nigeria",
        address="Abuja, Nigeria", postal_code="900001", linkedin_url="", website_url="",
        work_authorization="Requires sponsorship", requires_sponsorship=True,
        notice_period="Immediately available", salary_expectation="7",
        nationality="Nigerian", number_of_employers="2",
        highest_education=EducationRecord("Example University", "Bachelor of Laws (LLB)", "Law", "2020", "Nigeria"),
        employment_history=(
            EmploymentRecord("Human Resources Manager", "Example Ltd", "2024", "", True, "Managed HR operations and staff coordination."),
            EmploymentRecord("Legal Officer", "Example NGO", "2022", "2023", False, "Handled legal and compliance matters."),
        ),
        resume_path="", cover_letter_path="", supporting_document_path="",
    )


def test_answers_current_role_from_cv_facts():
    answer = answer_from_cv("What is your current job title?", profile())
    assert answer is not None
    assert answer.value == "Human Resources Manager"
    assert answer.source == "cv.employment.current.title"


def test_answers_relevant_experience_without_invention():
    answer = answer_from_cv("Please describe your relevant professional experience", profile())
    assert answer is not None
    assert "Human Resources Manager" in answer.value
    assert "Legal Officer" in answer.value
    assert "Managed HR operations" in answer.value


def test_answers_education_from_cv_facts():
    answer = answer_from_cv("What is your highest qualification?", profile())
    assert answer is not None
    assert "Bachelor of Laws" in answer.value
    assert "Example University" in answer.value


def test_country_location_is_country_only():
    answer = answer_from_cv("What is your location?", profile())
    assert answer is not None
    assert answer.value == "Nigeria"


def test_unknown_fact_is_refused():
    assert answer_from_cv("What is your security clearance number?", profile()) is None

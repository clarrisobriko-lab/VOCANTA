from dataclasses import replace

from automation.profile import ApplicantProfile, EmploymentRecord
from automation.semantic_answers import answer_application_question


def profile():
    return ApplicantProfile(
        first_name="Test", middle_name="Candidate", last_name="User", email="test@example.com",
        phone="+234000000000", city="Abuja", country="Nigeria", address="Abuja", postal_code="900001",
        linkedin_url="", website_url="", work_authorization="Requires sponsorship", requires_sponsorship=True,
        notice_period="Immediately available", salary_expectation="", nationality="Nigerian", region="Africa",
        employment_history=(
            EmploymentRecord("Human Resources Manager", "Example HR", "2024", current=True, summary="Managed onboarding, staff records, scheduling, policy and internal communications."),
            EmploymentRecord("Legal Officer", "Example Legal", "2022", "2023", summary="Managed case files, pleadings, client interviews, compliance records and complex legal documentation."),
            EmploymentRecord("Executive and administrative support", "Example Admin", "2021", "2022", summary="Coordinated schedules, records, stakeholders, meetings and administrative workflows."),
        ),
    )


def test_ea_question_prioritises_admin_evidence():
    p=profile(); a=answer_application_question("Describe any experience with administration, executive support, logistics, events or travel management",p,job_context="Executive Assistant corporate administrator scheduling meetings stakeholders")
    assert a is not None
    assert "Executive and administrative support" in a.value


def test_hr_vacancy_prioritises_hr_evidence():
    p=profile(); a=answer_application_question("Describe your relevant experience",p,job_context="HR operations onboarding employee records policy")
    assert a is not None
    assert a.value.index("Human Resources Manager") < a.value.index("Legal Officer")


def test_legal_vacancy_prioritises_legal_evidence():
    p=profile(); a=answer_application_question("Describe your relevant experience",p,job_context="legal compliance contracts case management pleadings")
    assert a is not None
    assert a.value.index("Legal Officer") < a.value.index("Human Resources Manager")


def test_missing_degree_result_is_not_invented():
    p=profile(); a=answer_application_question("What was your bachelor's university degree result? Include grading system",p)
    assert a is None


def test_known_degree_result_can_be_populated():
    p=replace(profile(),standard_answers={"what was your bachelor's university degree result grading system":"Third class, Bachelor of Laws (LLB), University of Uyo, 2020"})
    a=answer_application_question("What was your bachelor's university degree result? Include grading system",p)
    assert a is not None
    assert "Third class" in a.value


def test_generated_applicant_text_contains_no_em_dash():
    p=profile(); a=answer_application_question("Describe your relevant experience",p,job_context="Executive Assistant")
    assert a is not None
    assert "—" not in a.value and "–" not in a.value

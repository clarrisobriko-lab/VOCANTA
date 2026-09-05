from automation.form_profile_resolver import FormProfileResolver
from automation.profile import ApplicantProfile, EducationRecord, EmploymentRecord


def profile():
    return ApplicantProfile(
        first_name="Clarris",
        middle_name="Phegor",
        last_name="Obriko",
        email="clarris@example.com",
        phone="+2348000000000",
        city="Abuja",
        country="Nigeria",
        address="Abuja, Nigeria",
        postal_code="900001",
        linkedin_url="https://www.linkedin.com/in/example",
        website_url="",
        work_authorization="Requires sponsorship",
        requires_sponsorship=True,
        notice_period="Available immediately",
        salary_expectation="",
        highest_education=EducationRecord(
            institution="University of Uyo",
            degree="Bachelor of Laws (LLB)",
            discipline="Law",
            graduation_year="2020",
            country="Nigeria",
        ),
        employment_history=(
            EmploymentRecord(
                "Human Resources Manager",
                "Malachy Godian Enterprises",
                "2024",
                "",
                current=True,
                summary="HR policy, onboarding, records and staff training.",
            ),
            EmploymentRecord(
                "Legal Officer / Associate Counsel",
                "Legal Defence and Assistance Project (LEDAP)",
                "2022",
                "2023",
                summary="Legal representation, drafting and case support.",
            ),
            EmploymentRecord(
                "Legal Associate",
                "Malcolm Omirhobo & Co.",
                "2021",
                "2022",
                summary="Legal research, drafting and client support.",
            ),
        ),
    )


def test_repeated_employers_follow_cv_order():
    resolver = FormProfileResolver(profile())
    first = resolver.resolve("Company name")
    second = resolver.resolve("Employer")
    third = resolver.resolve("Organisation")
    assert first.value == "Malachy Godian Enterprises"
    assert second.value == "Legal Defence and Assistance Project (LEDAP)"
    assert third.value == "Malcolm Omirhobo & Co."
    assert first.source == "profile.employment_history[0].employer"


def test_repeated_titles_follow_cv_order():
    resolver = FormProfileResolver(profile())
    assert resolver.resolve("Job title").value == "Human Resources Manager"
    assert resolver.resolve("Position title").value == "Legal Officer / Associate Counsel"
    assert resolver.resolve("Role title").value == "Legal Associate"


def test_employment_years_follow_each_record():
    resolver = FormProfileResolver(profile())
    assert resolver.resolve("Start year").value == "2024"
    assert resolver.resolve("Start year").value == "2022"
    assert resolver.resolve("End year") is None
    assert resolver.resolve("End year").value == "2023"


def test_responsibilities_are_populated_from_profile_cv_record():
    resolver = FormProfileResolver(profile())
    first = resolver.resolve("Responsibilities")
    second = resolver.resolve("Job description")
    assert "onboarding" in first.value.lower()
    assert "legal representation" in second.value.lower()


def test_education_fields_are_populated_from_profile():
    resolver = FormProfileResolver(profile())
    assert resolver.resolve("University").value == "University of Uyo"
    assert resolver.resolve("Degree").value == "Bachelor of Laws (LLB)"
    assert resolver.resolve("Field of study").value == "Law"
    assert resolver.resolve("Graduation year").value == "2020"
    assert resolver.resolve("Country of institution").value == "Nigeria"


def test_narrative_role_question_is_not_mistaken_for_job_title():
    resolver = FormProfileResolver(profile())
    assert resolver.resolve("Describe your role and experience in HR") is None


def test_unknown_fields_are_not_invented():
    resolver = FormProfileResolver(profile())
    assert resolver.resolve("Security clearance number") is None

from automation.profile import ApplicantProfile
from automation.questions import Intent, identify_intent, resolve_question


def profile():
    return ApplicantProfile(
        first_name="Clarris",
        middle_name="Phegor",
        last_name="Obriko",
        email="clarris@example.com",
        phone="+2348055632432",
        city="Abuja",
        country="Nigeria",
        address="Abuja, Nigeria",
        postal_code="900106",
        linkedin_url="https://www.linkedin.com/in/example",
        website_url="",
        work_authorization="No, I require employer sponsorship",
        requires_sponsorship=True,
        notice_period="Available immediately",
        salary_expectation="7.00",
        demographics={"gender": "Female", "race": "Black or African American"},
        auto_fill_demographics=True,
    )


def test_gender_autofill_uses_approved_profile_value():
    resolution = resolve_question("Gender", profile())
    assert resolution.intent == Intent.DEMOGRAPHIC
    assert resolution.value == "Female"
    assert resolution.auto_fill_allowed is True


def test_race_autofill_uses_approved_profile_value():
    resolution = resolve_question("Race", profile())
    assert resolution.intent == Intent.DEMOGRAPHIC
    assert resolution.value == "Black or African American"
    assert resolution.auto_fill_allowed is True


def test_salary_variants_are_recognized():
    for label in ("Expected salary", "Salary expectations", "Salary requirements", "Expected compensation", "Hourly rate"):
        assert identify_intent(label) == Intent.SALARY
        resolution = resolve_question(label, profile())
        assert resolution.value == "7.00"
        assert resolution.auto_fill_allowed is True

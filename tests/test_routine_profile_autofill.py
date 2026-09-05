from automation.profile import ApplicantProfile
from automation.questions import Intent, identify_intent, resolve_question


def profile() -> ApplicantProfile:
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
        linkedin_url="https://www.linkedin.com/in/clarris-obriko-880b81104",
        website_url="",
        work_authorization="No, I require employer sponsorship",
        requires_sponsorship=True,
        notice_period="Available immediately",
        salary_expectation="$7.00 per hour",
        standard_answers={"how_did_you_hear": "LinkedIn"},
    )


def test_plain_country_field_uses_current_country():
    assert identify_intent("Country") == Intent.CURRENT_COUNTRY
    result = resolve_question("Country", profile())
    assert result.value == "Nigeria"
    assert result.auto_fill_allowed is True


def test_country_region_field_uses_current_country():
    result = resolve_question("Country / Region", profile())
    assert result.intent == Intent.CURRENT_COUNTRY
    assert result.value == "Nigeria"


def test_how_did_you_hear_uses_approved_standard_answer():
    result = resolve_question("How did you hear about us?", profile())
    assert result.value == "LinkedIn"
    assert result.auto_fill_allowed is True


def test_core_routine_profile_answers_are_available():
    candidate = profile()
    assert resolve_question("Nationality", candidate).value == "Nigerian"
    assert resolve_question("Do you require visa sponsorship?", candidate).value == "Yes"
    assert resolve_question("Notice period", candidate).value == "Available immediately"
    assert resolve_question("Desired salary", candidate).value == "$7.00 per hour"
    assert resolve_question("LinkedIn profile", candidate).value.endswith("880b81104")
    assert resolve_question("Postal code", candidate).value == "900106"

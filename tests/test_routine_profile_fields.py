from automation.profile import ApplicantProfile
from automation.questions import Intent, identify_intent, resolve_question


def profile():
    return ApplicantProfile(
        first_name="Clarris",
        middle_name="Phegor",
        last_name="Obriko",
        email="phegclarris@gmail.com",
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


def test_plain_country_is_current_country():
    assert identify_intent("Country") == Intent.CURRENT_COUNTRY
    assert resolve_question("Country", profile()).value == "Nigeria"


def test_country_region_is_current_country():
    assert resolve_question("Country / Region", profile()).value == "Nigeria"


def test_nationality_remains_distinct_from_country():
    assert identify_intent("Country of citizenship") == Intent.NATIONALITY
    assert resolve_question("Country of citizenship", profile()).value == "Nigerian"


def test_common_work_authorization_wording_is_recognized():
    assert identify_intent("Are you authorized to work in this country?") == Intent.WORK_AUTHORIZATION
    answer = resolve_question("Are you authorized to work in this country?", profile())
    assert answer.value == "No, I require employer sponsorship"
    assert answer.auto_fill_allowed


def test_how_did_you_hear_uses_approved_standard_answer():
    answer = resolve_question("How did you hear about us?", profile())
    assert answer.value == "LinkedIn"
    assert answer.auto_fill_allowed


def test_current_contact_values_are_available_for_autofill():
    p = profile()
    assert resolve_question("Phone", p).value == "+2348055632432"
    assert resolve_question("Postal code", p).value == "900106"
    assert resolve_question("LinkedIn", p).value == "https://www.linkedin.com/in/clarris-obriko-880b81104"

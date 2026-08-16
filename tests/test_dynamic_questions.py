from automation.profile import ApplicantProfile
from automation.questions import Intent, resolve_question


def profile(**changes):
    values = dict(first_name="Test", middle_name="", last_name="Candidate", email="test@example.com", phone="+2348000000000", city="Abuja", country="Nigeria", address="Address", postal_code="900001", linkedin_url="", website_url="", work_authorization="No, I require employer sponsorship", requires_sponsorship=True, notice_period="Immediately available", salary_expectation="", resume_path="", cover_letter_path="", supporting_document_path="", standard_answers={"why are you interested in this role": "I am interested because the role aligns with my approved experience and career direction."})
    values.update(changes)
    return ApplicantProfile(**values)


def test_dynamic_question_matches_approved_answer():
    result = resolve_question("Why are you interested in this role with our company?", profile())
    assert result.auto_fill_allowed is True
    assert result.confidence >= 60
    assert "approved experience" in result.value


def test_unapproved_written_question_is_not_invented():
    result = resolve_question("Describe a difficult conflict you personally resolved", profile())
    assert result.intent == Intent.WRITTEN_RESPONSE
    assert result.auto_fill_allowed is False
    assert result.value == ""


def test_employer_ai_restriction_overrides_saved_answer():
    result = resolve_question("Why are you interested in this role? Do not use AI generated content", profile())
    assert result.auto_fill_allowed is False
    assert "personally authored" in result.reason


def test_exact_approved_answer_has_full_confidence():
    result = resolve_question("Why are you interested in this role", profile())
    assert result.auto_fill_allowed is True
    assert result.confidence == 100

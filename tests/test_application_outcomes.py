from automation.browser import AutomationResult
from intelligence.application_outcomes import classify_outcome


def result(status, message="", confirmation_text=""):
    return AutomationResult(status, message, "", 0, confirmation_text=confirmation_text)


def test_confirmed_submission_is_applied():
    outcome = classify_outcome(result("SUBMITTED", "ok"))
    assert outcome.applied is True
    assert outcome.status == "APPLIED"
    assert outcome.confidence == 100


def test_confirmation_text_can_confirm_application():
    outcome = classify_outcome(result("UNKNOWN", confirmation_text="Thank you for applying"))
    assert outcome.applied is True
    assert outcome.confidence == 90


def test_requeue_is_not_marked_applied():
    outcome = classify_outcome(result("REQUEUE", "temporary network failure"))
    assert outcome.applied is False
    assert outcome.retry_later is True


def test_human_gate_is_explicit():
    outcome = classify_outcome(result("HUMAN_REQUIRED", "CAPTCHA"))
    assert outcome.human_required is True
    assert outcome.applied is False


def test_duplicate_is_treated_as_existing_application():
    outcome = classify_outcome(result("FAILED", "You have already applied"))
    assert outcome.status == "ALREADY_APPLIED"
    assert outcome.applied is True

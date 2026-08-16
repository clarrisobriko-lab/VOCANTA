from automation.application_pipeline import _apply_with_recovery
from automation.browser import AutomationResult
from automation.profile import ApplicantProfile
from core.models import Job


def profile():
    return ApplicantProfile(first_name="Test", middle_name="", last_name="Candidate", email="test@example.com", phone="+2348000000000", city="Abuja", country="Nigeria", address="Address", postal_code="900001", linkedin_url="", website_url="", work_authorization="No", requires_sponsorship=False, notice_period="Immediate", salary_expectation="", resume_path="", cover_letter_path="", supporting_document_path="")


def job():
    return Job(company="Acme", title="Executive Assistant", location="Remote", source="Test", url="https://example.com/job")


class Engine:
    calls = 0
    results = []
    def __init__(self, _profile): pass
    def apply(self, _url, _job_id):
        type(self).calls += 1
        result = type(self).results.pop(0)
        if isinstance(result, Exception): raise result
        return result


def test_transient_failure_retries_then_succeeds():
    Engine.calls = 0
    Engine.results = [TimeoutError("navigation timed out"), AutomationResult("SUBMITTED", "ok", "", 1)]
    sleeps = []
    result = _apply_with_recovery(job(), 1, profile(), Engine, sleep_fn=sleeps.append)
    assert result.status == "SUBMITTED"
    assert Engine.calls == 2
    assert sleeps == [5]


def test_human_gate_does_not_retry():
    Engine.calls = 0
    Engine.results = [AutomationResult("HUMAN_REQUIRED", "CAPTCHA verify you are human", "", 0)]
    result = _apply_with_recovery(job(), 1, profile(), Engine, sleep_fn=lambda _: None)
    assert result.status == "HUMAN_REQUIRED"
    assert Engine.calls == 1


def test_terminal_closed_job_does_not_retry():
    Engine.calls = 0
    Engine.results = [AutomationResult("FAILED", "position closed and no longer accepting applications", "", 0)]
    result = _apply_with_recovery(job(), 1, profile(), Engine, sleep_fn=lambda _: None)
    assert result.status == "FAILED"
    assert Engine.calls == 1

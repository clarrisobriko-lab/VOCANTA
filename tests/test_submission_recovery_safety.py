from automation.application_pipeline import _apply_with_recovery
from automation.browser import AutomationResult


class DummyJob:
    url = "https://example.com/job/1"


class DummyProfile:
    pass


def _factory(results, calls):
    class Engine:
        def __init__(self, profile):
            self.profile = profile

        def apply(self, url, job_id):
            calls.append((url, job_id))
            result = results.pop(0)
            if isinstance(result, Exception):
                raise result
            return result

    return Engine


def test_unknown_submission_is_never_retried():
    calls = []
    results = [AutomationResult("UNKNOWN", "submit clicked but confirmation missing", "shot.png", 10)]
    result = _apply_with_recovery(DummyJob(), 1, DummyProfile(), _factory(results, calls), sleep_fn=lambda _: None)
    assert result.status == "UNKNOWN"
    assert len(calls) == 1


def test_auto_submitted_is_terminal_success():
    calls = []
    results = [AutomationResult("AUTO_SUBMITTED", "confirmed", "shot.png", 10, confirmation_url="https://example.com/thanks")]
    result = _apply_with_recovery(DummyJob(), 1, DummyProfile(), _factory(results, calls), sleep_fn=lambda _: None)
    assert result.status == "AUTO_SUBMITTED"
    assert len(calls) == 1


def test_ready_to_review_is_not_retried():
    calls = []
    results = [AutomationResult("READY_TO_REVIEW", "manual answer required", "shot.png", 9)]
    result = _apply_with_recovery(DummyJob(), 1, DummyProfile(), _factory(results, calls), sleep_fn=lambda _: None)
    assert result.status == "READY_TO_REVIEW"
    assert len(calls) == 1


def test_transient_pre_submit_failure_retries_within_budget():
    calls = []
    results = [RuntimeError("network timeout"), AutomationResult("AUTO_SUBMITTED", "confirmed", "shot.png", 10)]
    result = _apply_with_recovery(DummyJob(), 1, DummyProfile(), _factory(results, calls), max_attempts=3, sleep_fn=lambda _: None)
    assert result.status == "AUTO_SUBMITTED"
    assert len(calls) == 2

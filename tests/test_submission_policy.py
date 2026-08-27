import pytest

from automation.submission_policy import policy_for_url, reconcile_status, should_retry


@pytest.mark.parametrize("url,name", [
    ("https://boards.greenhouse.io/example/jobs/1", "GREENHOUSE"),
    ("https://jobs.lever.co/example/1", "LEVER"),
    ("https://jobs.ashbyhq.com/example/1", "ASHBY"),
    ("https://jobs.smartrecruiters.com/example/1", "SMARTRECRUITERS"),
    ("https://example.wd5.myworkdayjobs.com/job/1", "WORKDAY"),
])
def test_production_adapters_preserve_auto_submit_capability(url, name):
    policy = policy_for_url(url)
    assert policy.adapter.name == name
    assert policy.may_auto_submit is True
    assert policy.requires_review is False


def test_generic_adapter_remains_review_only():
    policy = policy_for_url("https://careers.example.com/job/1")
    assert policy.adapter.name == "GENERIC"
    assert policy.may_auto_submit is False
    assert policy.requires_review is True


def test_reconciliation_preserves_critical_states():
    assert reconcile_status("submitted") == "SUBMITTED"
    assert reconcile_status("submission_unverified") == "UNKNOWN"
    assert reconcile_status("unknown") == "UNKNOWN"
    assert reconcile_status("human_required") == "AUTH_REQUIRED"
    assert reconcile_status("ready_to_review") == "READY_TO_REVIEW"


def test_unknown_and_submitted_are_never_automatically_retried():
    assert should_retry("UNKNOWN") is False
    assert should_retry("SUBMISSION_UNVERIFIED") is False
    assert should_retry("SUBMITTED") is False
    assert should_retry("FAILED") is True

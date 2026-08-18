from automation.live_submission_gate import LiveGateStatus, LiveSubmissionAuthorization, evaluate_live_submission_gate


def _auth(**overrides):
    values = dict(employer="Automattic", job_url="https://automattic.com/work-with-us/job/example/", authorized=True, dry_run_passed=True, package_validated=True, supported_ats=True, unresolved_ambiguous_submission=False)
    values.update(overrides)
    return LiveSubmissionAuthorization(**values)


def test_ready_only_when_all_live_preconditions_pass():
    assert evaluate_live_submission_gate(_auth()).status == LiveGateStatus.READY


def test_requires_explicit_authorization():
    decision = evaluate_live_submission_gate(_auth(authorized=False))
    assert decision.status == LiveGateStatus.BLOCKED
    assert "authorization" in decision.reason


def test_ambiguous_prior_submission_blocks_retry():
    decision = evaluate_live_submission_gate(_auth(unresolved_ambiguous_submission=True))
    assert decision.status == LiveGateStatus.BLOCKED
    assert "reconciliation" in decision.reason


def test_dry_run_and_package_validation_are_mandatory():
    assert evaluate_live_submission_gate(_auth(dry_run_passed=False)).status == LiveGateStatus.BLOCKED
    assert evaluate_live_submission_gate(_auth(package_validated=False)).status == LiveGateStatus.BLOCKED


def test_unknown_ats_fails_closed():
    assert evaluate_live_submission_gate(_auth(supported_ats=False)).status == LiveGateStatus.BLOCKED

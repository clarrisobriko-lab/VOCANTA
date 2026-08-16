from automation.recovery import RecoveryAction, decide_recovery


def test_transient_failure_retries_with_backoff():
    decision = decide_recovery("Navigation timed out", 1)
    assert decision.action == RecoveryAction.RETRY
    assert decision.retryable is True
    assert decision.delay_seconds == 5


def test_exhausted_transient_failure_requeues():
    decision = decide_recovery("503 service unavailable", 3)
    assert decision.action == RecoveryAction.REQUEUE
    assert decision.delay_seconds == 300


def test_human_verification_is_not_bypassed():
    decision = decide_recovery("CAPTCHA verify you are human", 1)
    assert decision.action == RecoveryAction.HUMAN_REQUIRED
    assert decision.retryable is False


def test_closed_job_is_terminal():
    decision = decide_recovery("This position is closed and no longer accepting applications", 1)
    assert decision.action == RecoveryAction.STOP
    assert decision.retryable is False


def test_unknown_failure_stops_for_diagnostics():
    decision = decide_recovery("unexpected employer-specific widget", 1)
    assert decision.action == RecoveryAction.STOP

from datetime import datetime, timezone

import pytest

from automation.live_execution_record import LiveOutcome, new_record, should_retry


def test_submitted_requires_confirmation_evidence():
    with pytest.raises(ValueError):
        new_record(employer="Automattic", role="Target Role", target_url="https://example.test/job",
                   ats="greenhouse", outcome=LiveOutcome.SUBMITTED)


def test_confirmed_submission_is_not_retried():
    record = new_record(employer="Automattic", role="Target Role", target_url="https://example.test/job",
                        ats="greenhouse", outcome=LiveOutcome.SUBMITTED,
                        confirmation_evidence="application received", application_id="abc123",
                        now=datetime(2026, 8, 18, tzinfo=timezone.utc))
    assert record.confirmed is True
    assert should_retry(record) is False


def test_unknown_live_outcome_is_not_retried():
    record = new_record(employer="Automattic", role="Target Role", target_url="https://example.test/job",
                        ats="greenhouse", outcome=LiveOutcome.UNKNOWN,
                        message="navigation timed out after submit")
    assert record.confirmed is False
    assert should_retry(record) is False


def test_failed_pre_submission_attempt_can_be_retried():
    record = new_record(employer="Automattic", role="Target Role", target_url="https://example.test/job",
                        ats="greenhouse", outcome=LiveOutcome.FAILED, message="pre-submit validation failure")
    assert should_retry(record) is True

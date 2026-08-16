from datetime import datetime, timezone

from intelligence.follow_up import evaluate_follow_up

NOW = datetime(2026, 8, 16, tzinfo=timezone.utc)


def test_first_follow_up_due_after_seven_days():
    result = evaluate_follow_up("2026-08-01T00:00:00+00:00", now=NOW)
    assert result.due is True
    assert result.action == "FIRST_FOLLOW_UP"


def test_recent_application_waits():
    result = evaluate_follow_up("2026-08-14T00:00:00+00:00", now=NOW)
    assert result.due is False
    assert result.action == "FIRST_FOLLOW_UP"


def test_second_follow_up_after_first_contact():
    result = evaluate_follow_up("2026-08-01T00:00:00+00:00", follow_up_count=1, now=NOW)
    assert result.due is True
    assert result.action == "SECOND_FOLLOW_UP"


def test_follow_up_limit_prevents_spam():
    result = evaluate_follow_up("2026-07-01T00:00:00+00:00", follow_up_count=2, now=NOW)
    assert result.due is False
    assert result.action == "NONE"


def test_interview_stops_follow_up():
    result = evaluate_follow_up("2026-07-01T00:00:00+00:00", status="INTERVIEW", now=NOW)
    assert result.due is False
    assert result.action == "NONE"

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone


@dataclass(frozen=True, slots=True)
class FollowUpDecision:
    due: bool
    action: str
    due_at: str
    reason: str


def evaluate_follow_up(applied_at: str, *, status: str = "APPLIED", follow_up_count: int = 0, now: datetime | None = None, first_wait_days: int = 7, second_wait_days: int = 7) -> FollowUpDecision:
    now = now or datetime.now(timezone.utc)
    state = (status or "").upper()
    if state in {"INTERVIEW", "OFFER", "REJECTED", "WITHDRAWN", "CLOSED"}:
        return FollowUpDecision(False, "NONE", "", f"application is already in terminal/advanced state: {state}")
    try:
        applied = datetime.fromisoformat(applied_at.replace("Z", "+00:00"))
    except (ValueError, AttributeError):
        return FollowUpDecision(False, "NONE", "", "application date unavailable")
    if applied.tzinfo is None:
        applied = applied.replace(tzinfo=timezone.utc)
    if follow_up_count <= 0:
        due_at = applied + timedelta(days=first_wait_days); action = "FIRST_FOLLOW_UP"
    elif follow_up_count == 1:
        due_at = applied + timedelta(days=first_wait_days + second_wait_days); action = "SECOND_FOLLOW_UP"
    else:
        return FollowUpDecision(False, "NONE", "", "follow-up limit reached")
    return FollowUpDecision(now >= due_at, action, due_at.isoformat(), "follow-up due" if now >= due_at else "waiting period not elapsed")

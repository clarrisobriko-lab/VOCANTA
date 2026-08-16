from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class RecoveryAction(str, Enum):
    RETRY = "RETRY"
    REQUEUE = "REQUEUE"
    HUMAN_REQUIRED = "HUMAN_REQUIRED"
    STOP = "STOP"


@dataclass(frozen=True, slots=True)
class RecoveryDecision:
    action: RecoveryAction
    retryable: bool
    delay_seconds: int
    reason: str


TRANSIENT_MARKERS = (
    "timeout", "timed out", "network", "connection reset", "temporarily unavailable",
    "service unavailable", "502", "503", "504", "navigation failed",
)
HUMAN_MARKERS = (
    "captcha", "verify you are human", "human verification", "verification code",
    "two-factor", "2fa", "email verification",
)
TERMINAL_MARKERS = (
    "job closed", "position closed", "no longer accepting", "application deadline has passed",
    "already applied", "duplicate application",
)


def decide_recovery(error: str, attempt: int, max_attempts: int = 3) -> RecoveryDecision:
    text = " ".join((error or "").lower().split())
    if any(marker in text for marker in HUMAN_MARKERS):
        return RecoveryDecision(RecoveryAction.HUMAN_REQUIRED, False, 0, "human verification required")
    if any(marker in text for marker in TERMINAL_MARKERS):
        return RecoveryDecision(RecoveryAction.STOP, False, 0, "terminal application state")
    if any(marker in text for marker in TRANSIENT_MARKERS):
        if attempt < max_attempts:
            delay = min(60, 5 * (2 ** max(0, attempt - 1)))
            return RecoveryDecision(RecoveryAction.RETRY, True, delay, "transient browser or network failure")
        return RecoveryDecision(RecoveryAction.REQUEUE, True, 300, "retry budget exhausted; requeue later")
    return RecoveryDecision(RecoveryAction.STOP, False, 0, "unclassified failure requires diagnostics")

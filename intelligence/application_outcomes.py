from __future__ import annotations

from dataclasses import dataclass

from automation.browser import AutomationResult


@dataclass(frozen=True, slots=True)
class Outcome:
    status: str
    applied: bool
    retry_later: bool
    human_required: bool
    confidence: int
    reason: str


def classify_outcome(result: AutomationResult | None) -> Outcome:
    if result is None:
        return Outcome("NOT_ATTEMPTED", False, False, False, 100, "application was not attempted")
    status = (result.status or "").upper()
    text = f"{status} {result.message} {result.confirmation_text}".lower()
    if status in {"SUBMITTED", "SUCCESS"} or any(term in text for term in ("application submitted", "thank you for applying", "application received")):
        return Outcome("APPLIED", True, False, False, 100 if status in {"SUBMITTED", "SUCCESS"} else 90, "submission confirmed")
    if status == "REQUEUE":
        return Outcome("REQUEUE", False, True, False, 95, "temporary failure; retry later")
    if status == "HUMAN_REQUIRED" or any(term in text for term in ("captcha", "verify you are human", "verification code", "two-factor")):
        return Outcome("HUMAN_REQUIRED", False, False, True, 100, "human verification required")
    if any(term in text for term in ("already applied", "duplicate application")):
        return Outcome("ALREADY_APPLIED", True, False, False, 95, "employer reports an existing application")
    if any(term in text for term in ("position closed", "job closed", "no longer accepting")):
        return Outcome("CLOSED", False, False, False, 95, "vacancy is no longer accepting applications")
    return Outcome("FAILED", False, False, False, 60, result.message or "submission not confirmed")

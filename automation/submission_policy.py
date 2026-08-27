from __future__ import annotations

from dataclasses import dataclass

from automation.ats import ATSAdapter, adapter_for_url


AUTO_SUBMIT_ADAPTERS = frozenset({"GREENHOUSE", "LEVER"})
REVIEW_ONLY_ADAPTERS = frozenset({"ASHBY", "SMARTRECRUITERS", "WORKDAY", "GENERIC"})
TERMINAL_NO_RETRY = frozenset({"SUBMITTED", "SUCCESS", "AUTO_SUBMITTED", "CONFIRMED", "UNKNOWN", "SUBMISSION_UNVERIFIED"})


@dataclass(frozen=True, slots=True)
class SubmissionPolicy:
    adapter: ATSAdapter
    may_auto_submit: bool
    requires_review: bool
    reason: str


def policy_for_url(url: str) -> SubmissionPolicy:
    adapter = adapter_for_url(url)
    if adapter.name in AUTO_SUBMIT_ADAPTERS:
        return SubmissionPolicy(adapter, True, False, "validated ATS adapter may auto submit")
    return SubmissionPolicy(adapter, False, True, "ATS requires review before final submission")


def reconcile_status(status: str) -> str:
    value = (status or "").strip().upper()
    if value in {"SUBMITTED", "SUCCESS", "AUTO_SUBMITTED", "CONFIRMED"}:
        return "SUBMITTED"
    if value in {"UNKNOWN", "SUBMISSION_UNVERIFIED"}:
        return "UNKNOWN"
    if value in {"AUTH_REQUIRED", "ACCOUNT_REQUIRED", "HUMAN_REQUIRED", "HUMAN_VERIFICATION", "MANUAL_REQUIRED"}:
        return "AUTH_REQUIRED"
    if value in {"READY_TO_REVIEW", "REVIEW_REQUIRED"}:
        return "READY_TO_REVIEW"
    return value or "UNKNOWN"


def should_retry(status: str) -> bool:
    return (status or "").strip().upper() not in TERMINAL_NO_RETRY

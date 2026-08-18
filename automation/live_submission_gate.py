from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class LiveGateStatus(str, Enum):
    READY = "READY"
    BLOCKED = "BLOCKED"


@dataclass(frozen=True, slots=True)
class LiveSubmissionAuthorization:
    employer: str
    job_url: str
    authorized: bool
    dry_run_passed: bool
    package_validated: bool
    supported_ats: bool
    unresolved_ambiguous_submission: bool = False


@dataclass(frozen=True, slots=True)
class LiveGateDecision:
    status: LiveGateStatus
    reason: str


def evaluate_live_submission_gate(auth: LiveSubmissionAuthorization) -> LiveGateDecision:
    """Fail closed unless every controlled-live precondition is satisfied."""
    if not auth.employer.strip() or not auth.job_url.strip():
        return LiveGateDecision(LiveGateStatus.BLOCKED, "target employer/job is missing")
    if auth.unresolved_ambiguous_submission:
        return LiveGateDecision(LiveGateStatus.BLOCKED, "ambiguous prior submission requires reconciliation")
    if not auth.supported_ats:
        return LiveGateDecision(LiveGateStatus.BLOCKED, "ATS is not approved for controlled live execution")
    if not auth.package_validated:
        return LiveGateDecision(LiveGateStatus.BLOCKED, "application package has not passed validation")
    if not auth.dry_run_passed:
        return LiveGateDecision(LiveGateStatus.BLOCKED, "controlled dry run has not passed")
    if not auth.authorized:
        return LiveGateDecision(LiveGateStatus.BLOCKED, "explicit live-submit authorization is required")
    return LiveGateDecision(LiveGateStatus.READY, "controlled live submission authorized")

from dataclasses import dataclass

from core.models import Job
from intelligence.eligibility import assess_eligibility


@dataclass(frozen=True, slots=True)
class RestrictionAssessment:
    blocked: bool
    reason: str
    category: str


def assess_restrictions(job: Job) -> RestrictionAssessment:
    decision = assess_eligibility(job)
    if "GEOGRAPHY_RESTRICTED" in decision.reason_codes:
        return RestrictionAssessment(True, decision.primary_reason, "GEOGRAPHY")
    if "LOCAL_LANGUAGE_REQUIRED" in decision.reason_codes:
        return RestrictionAssessment(True, decision.primary_reason, "LANGUAGE")
    if "MARKET_UNSUPPORTED" in decision.reason_codes:
        return RestrictionAssessment(True, decision.primary_reason, "GEOGRAPHY")
    return RestrictionAssessment(False, "", "")

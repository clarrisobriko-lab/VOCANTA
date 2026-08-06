from dataclasses import dataclass

from core.models import Job
from intelligence.eligibility import assess_eligibility as assess_decision


@dataclass(frozen=True, slots=True)
class EligibilityAssessment:
    sponsorship: str
    relocation: str
    organisation: str
    verdict: str
    reason_codes: tuple[str, ...]
    primary_reason: str
    rule_version: str


def assess_eligibility(job: Job) -> EligibilityAssessment:
    decision = assess_decision(job)
    return EligibilityAssessment(
        sponsorship=decision.sponsorship_label,
        relocation=decision.relocation_label,
        organisation=("NGO" if decision.ngo_label != "CORPORATE" else "CORPORATE"),
        verdict=decision.recommendation,
        reason_codes=decision.reason_codes,
        primary_reason=decision.primary_reason,
        rule_version=decision.rule_version,
    )

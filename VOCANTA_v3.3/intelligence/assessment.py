from dataclasses import dataclass

from core.models import Job
from intelligence.eligibility import assess_eligibility


@dataclass(frozen=True, slots=True)
class JobIntelligence:
    sponsorship_score: int
    sponsorship_label: str
    relocation_label: str
    international_hiring_label: str
    confidence: int
    ngo_label: str
    ngo_bonus: int
    blocked: bool
    block_reason: str
    block_category: str
    recommendation: str
    decision_verdict: str
    decision_reason_codes: tuple[str, ...]
    decision_evidence: tuple[str, ...]
    rule_version: str


def assess_job(job: Job) -> JobIntelligence:
    decision = assess_eligibility(job)
    if "GEOGRAPHY_RESTRICTED" in decision.reason_codes or "MARKET_UNSUPPORTED" in decision.reason_codes:
        block_category = "GEOGRAPHY"
    elif "LOCAL_LANGUAGE_REQUIRED" in decision.reason_codes:
        block_category = "LANGUAGE"
    elif decision.blocked:
        block_category = "ELIGIBILITY"
    else:
        block_category = ""

    return JobIntelligence(
        sponsorship_score=decision.sponsorship_score,
        sponsorship_label=decision.sponsorship_label,
        relocation_label=decision.relocation_label,
        international_hiring_label=decision.international_hiring_label,
        confidence=decision.confidence,
        ngo_label=decision.ngo_label,
        ngo_bonus=decision.ngo_bonus,
        blocked=decision.blocked,
        block_reason=decision.primary_reason if decision.blocked else "",
        block_category=block_category,
        recommendation=decision.recommendation,
        decision_verdict=decision.verdict,
        decision_reason_codes=decision.reason_codes,
        decision_evidence=decision.evidence,
        rule_version=decision.rule_version,
    )

from dataclasses import dataclass

from core.models import Job
from intelligence.eligibility import assess_eligibility


@dataclass(frozen=True, slots=True)
class SponsorshipAssessment:
    score: int
    label: str
    relocation: str
    international_hiring: str
    confidence: int


def assess_sponsorship(job: Job) -> SponsorshipAssessment:
    decision = assess_eligibility(job)
    return SponsorshipAssessment(
        score=decision.sponsorship_score,
        label=decision.sponsorship_label,
        relocation=decision.relocation_label,
        international_hiring=decision.international_hiring_label,
        confidence=decision.confidence,
    )

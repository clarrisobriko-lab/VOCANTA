from dataclasses import dataclass

from core.models import Job
from intelligence.assessment import JobIntelligence


PERK_SIGNALS = {
    "relocation": 10,
    "visa sponsorship": 12,
    "health insurance": 4,
    "private medical": 4,
    "pension": 3,
    "annual bonus": 4,
    "performance bonus": 4,
    "equity": 4,
    "stock options": 4,
    "remote work": 3,
    "work from anywhere": 5,
    "paid time off": 3,
    "professional development": 3,
    "training budget": 3,
    "housing": 5,
    "accommodation": 5,
    "flight": 4,
}


@dataclass(frozen=True, slots=True)
class OpportunityAssessment:
    score: int
    high_value: bool
    perk_signals: tuple[str, ...]
    rationale: str


def assess_opportunity(
    job: Job,
    intelligence: JobIntelligence,
    minimum_job_score: int,
    minimum_opportunity_score: int,
) -> OpportunityAssessment:
    text = " ".join(
        (
            job.title,
            job.description,
            job.salary,
            job.employment_type,
            job.location,
        )
    ).lower()

    matched = tuple(
        phrase for phrase in PERK_SIGNALS
        if phrase in text
    )
    perk_bonus = min(
        18,
        sum(PERK_SIGNALS[phrase] for phrase in matched),
    )

    sponsorship_bonus = {
        "YES": 12,
        "POSSIBLE": 6,
        "UNKNOWN": 0,
        "NO": -20,
    }.get(intelligence.sponsorship_label, 0)

    relocation_bonus = 8 if intelligence.relocation_label == "YES" else 0
    ngo_bonus = 6 if intelligence.ngo_label == "NGO_PRIORITY" else 0
    recommendation_bonus = {
        "PRIORITY": 8,
        "APPLY": 2,
        "RESEARCH": -12,
        "IGNORE": -40,
    }.get(intelligence.recommendation, 0)

    score = max(
        0,
        min(
            100,
            int(job.score)
            + perk_bonus
            + sponsorship_bonus
            + relocation_bonus
            + ngo_bonus
            + recommendation_bonus,
        ),
    )

    high_value = (
        not intelligence.blocked
        and intelligence.decision_verdict in {"PRIORITY", "APPLY"}
        and intelligence.recommendation in {"PRIORITY", "APPLY"}
        and (
            int(job.score) >= minimum_job_score
            or score >= minimum_opportunity_score
        )
    )

    reasons = [
        f"job score {job.score}",
        f"opportunity score {score}",
        f"track {intelligence.recommendation}",
        f"visa {intelligence.sponsorship_label}",
    ]
    if matched:
        reasons.append("perks: " + ", ".join(matched[:6]))

    return OpportunityAssessment(
        score=score,
        high_value=high_value,
        perk_signals=matched,
        rationale="; ".join(reasons),
    )

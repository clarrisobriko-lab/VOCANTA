from config.settings import (
    ENTRY_LEVEL_BONUS,
    EXCLUDED_TITLE_TERMS,
    HIRING_URGENCY_TERMS,
    MANAGER_LEVEL_PENALTY,
    MID_LEVEL_BONUS,
    PROFILE_KEYWORDS,
    SENIORITY_PENALTIES,
    TARGET_ROLE_WEIGHTS,
)
from core.models import Job
from intelligence.eligibility import assess_eligibility


class Scorer:
    def score(self, job: Job) -> int:
        title = job.title.lower()
        text = f"{job.title} {job.description} {job.employment_type}".lower()

        if any(term in title for term in EXCLUDED_TITLE_TERMS):
            return 0

        decision = assess_eligibility(job)
        if decision.blocked:
            return 0

        role_points = max((weight for term, weight in TARGET_ROLE_WEIGHTS.items() if term in title), default=0)
        if role_points == 0:
            return 0

        role_score = min(100, role_points * 2)
        profile_score = min(100, sum(points for term, points in PROFILE_KEYWORDS.items() if term in text) * 4)
        sponsorship_bonus = {"YES": 12, "POSSIBLE": 6}.get(decision.sponsorship_label, 0)
        relocation_bonus = 18 if decision.relocation_label == "YES" else 0
        eligibility_penalty = 12 if decision.verdict == "REVIEW" else 0
        urgency_bonus = max((points for term, points in HIRING_URGENCY_TERMS.items() if term in text), default=0)
        seniority_penalty = max((penalty for term, penalty in SENIORITY_PENALTIES.items() if term in title), default=0)

        career_adjustment = 0
        if decision.career_level == "ENTRY":
            career_adjustment = ENTRY_LEVEL_BONUS
        elif decision.career_level == "MID":
            career_adjustment = MID_LEVEL_BONUS
            if "manager" in title:
                career_adjustment -= MANAGER_LEVEL_PENALTY

        base_score = role_score * 0.45 + decision.market_score * 0.35 + profile_score * 0.20
        final_score = (
            base_score + decision.language_penalty + sponsorship_bonus + relocation_bonus
            + decision.ngo_bonus + urgency_bonus
            + max(-20, min(decision.sponsorship_score // 3, 20))
            + career_adjustment - eligibility_penalty - seniority_penalty
        )
        return max(0, min(round(final_score), 100))

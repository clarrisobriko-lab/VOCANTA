from dataclasses import dataclass

from automation.ats_match import analyse_ats_match
from config.settings import (
    ENTRY_LEVEL_BONUS, EXCLUDED_TITLE_TERMS, HIRING_URGENCY_TERMS,
    MANAGER_LEVEL_PENALTY, MID_LEVEL_BONUS, PROFILE_KEYWORDS,
    SENIORITY_PENALTIES, TARGET_ROLE_WEIGHTS,
)
from core.models import Job
from intelligence.eligibility import assess_eligibility
from intelligence.opportunity_intelligence import analyse_opportunity


@dataclass(frozen=True, slots=True)
class ApplicationDecision:
    score: int
    base_score: int
    ats_score: int
    should_apply: bool
    matched_skills: tuple[str, ...]
    missing_skills: tuple[str, ...]
    reason: str


class Scorer:
    AUTO_APPLY_THRESHOLD = 60
    MIN_ATS_COVERAGE = 50

    def _base_score(self, job: Job) -> int:
        title = job.title.lower()
        text = f"{job.title} {job.description} {job.employment_type}".lower()
        if any(term in title for term in EXCLUDED_TITLE_TERMS): return 0
        decision = assess_eligibility(job)
        if decision.blocked: return 0
        role_points = max((weight for term, weight in TARGET_ROLE_WEIGHTS.items() if term in title), default=0)
        if role_points == 0: return 0
        role_score = min(100, role_points * 2)
        profile_score = min(100, sum(points for term, points in PROFILE_KEYWORDS.items() if term in text) * 4)
        sponsorship_bonus = {"YES": 12, "POSSIBLE": 6}.get(decision.sponsorship_label, 0)
        relocation_bonus = 18 if decision.relocation_label == "YES" else 0
        eligibility_penalty = 12 if decision.verdict == "REVIEW" else 0
        urgency_bonus = max((points for term, points in HIRING_URGENCY_TERMS.items() if term in text), default=0)
        seniority_penalty = max((penalty for term, penalty in SENIORITY_PENALTIES.items() if term in title), default=0)
        career_adjustment = ENTRY_LEVEL_BONUS if decision.career_level == "ENTRY" else MID_LEVEL_BONUS if decision.career_level == "MID" else 0
        if decision.career_level == "MID" and "manager" in title: career_adjustment -= MANAGER_LEVEL_PENALTY
        base_score = role_score * 0.45 + decision.market_score * 0.35 + profile_score * 0.20
        final_score = base_score + decision.language_penalty + sponsorship_bonus + relocation_bonus + decision.ngo_bonus + urgency_bonus + max(-20, min(decision.sponsorship_score // 3, 20)) + career_adjustment - eligibility_penalty - seniority_penalty
        return max(0, min(round(final_score), 100))

    def evaluate(self, job: Job) -> ApplicationDecision:
        base = self._base_score(job)
        if base == 0:
            return ApplicationDecision(0, 0, 0, False, (), (), "Rejected by role or eligibility filters")
        ats = analyse_ats_match(job)
        opportunity = analyse_opportunity(job)
        composite = round(base * 0.50 + ats.score * 0.30 + opportunity.employer_score * 0.12 + opportunity.salary_score * 0.08)
        hard_gap = bool(ats.required_skills) and ats.score < self.MIN_ATS_COVERAGE
        should_apply = composite >= self.AUTO_APPLY_THRESHOLD and not hard_gap
        if hard_gap:
            reason = f"ATS coverage {ats.score}% is below {self.MIN_ATS_COVERAGE}% minimum"
        elif composite < self.AUTO_APPLY_THRESHOLD:
            reason = f"Composite score {composite} is below auto apply threshold {self.AUTO_APPLY_THRESHOLD}"
        else:
            reason = f"Eligible for automatic application; employer {opportunity.employer_score}/100, salary {opportunity.salary_score}/100"
        return ApplicationDecision(composite, base, ats.score, should_apply, ats.matched_skills, ats.missing_skills, reason)

    def score(self, job: Job) -> int:
        return self.evaluate(job).score

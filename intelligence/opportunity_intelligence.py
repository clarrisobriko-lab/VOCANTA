from __future__ import annotations

import re
from dataclasses import dataclass

from automation.ats_match import analyse_ats_match
from core.models import Job
from intelligence.employer_intelligence import analyse_job


@dataclass(frozen=True, slots=True)
class OpportunityIntelligence:
    skill_gap_score: int
    matched_skills: tuple[str, ...]
    missing_skills: tuple[str, ...]
    salary_score: int
    employer_score: int
    opportunity_score: int
    salary_text: str


def skill_gap_score(job: Job) -> tuple[int, tuple[str, ...], tuple[str, ...]]:
    ats = analyse_ats_match(job)
    return ats.score, ats.matched_skills, ats.missing_skills


def salary_score(salary_text: str) -> int:
    if not salary_text:
        return 50
    values = [float(v.replace(",", "")) for v in re.findall(r"\d[\d,]*(?:\.\d+)?", salary_text)]
    if not values:
        return 50
    amount = sum(values[:2]) / min(2, len(values))
    lowered = salary_text.lower()
    if any(token in lowered for token in ("hour", "/hr", " hr")):
        amount *= 2080
    elif any(token in lowered for token in ("month", "/mo", " mo")):
        amount *= 12
    currency_bonus = 8 if any(symbol in salary_text for symbol in ("£", "$", "€")) else 0
    if amount >= 70000:
        base = 95
    elif amount >= 50000:
        base = 85
    elif amount >= 35000:
        base = 75
    elif amount >= 25000:
        base = 65
    else:
        base = 55
    return min(100, base + currency_bonus)


def employer_score(job: Job) -> int:
    intel = analyse_job(job)
    score = 50
    if intel.remote_signal == "GLOBAL_REMOTE":
        score += 25
    elif intel.remote_signal == "REMOTE":
        score += 12
    if any(host in intel.employer_domain for host in ("greenhouse", "lever.co", "ashbyhq", "smartrecruiters", "workday")):
        score += 15
    if job.company and job.company.lower() not in {"unknown", "n/a"}:
        score += 10
    return min(score, 100)


def analyse_opportunity(job: Job) -> OpportunityIntelligence:
    gap, matched, missing = skill_gap_score(job)
    intel = analyse_job(job)
    salary = salary_score(intel.salary_text)
    employer = employer_score(job)
    overall = round(gap * 0.55 + employer * 0.30 + salary * 0.15)
    return OpportunityIntelligence(gap, matched, missing, salary, employer, overall, intel.salary_text)

from dataclasses import dataclass

from automation.claims_ledger import evidence_for, verified_skill_keys
from automation.tailoring import classify_job, extract_keywords
from core.models import Job


@dataclass(frozen=True, slots=True)
class ATSMatchResult:
    score: int
    category: str
    required_skills: tuple[str, ...]
    matched_skills: tuple[str, ...]
    missing_skills: tuple[str, ...]


def verified_skill_set(category: str) -> set[str]:
    """Return only skills backed by the applicant claims ledger.

    Category is retained for API compatibility. It must not manufacture skills.
    """
    del category
    return verified_skill_keys()


def verified_job_keywords(job: Job) -> tuple[str, ...]:
    """Return detected vacancy requirements with concrete applicant evidence."""
    required = extract_keywords(job)
    return tuple(skill for skill in required if evidence_for(skill))


def analyse_ats_match(job: Job) -> ATSMatchResult:
    """Score semantic ATS coverage without inventing unsupported qualifications."""
    category = classify_job(job)
    required = extract_keywords(job)
    matched = tuple(skill for skill in required if evidence_for(skill))
    missing = tuple(skill for skill in required if not evidence_for(skill))
    score = 100 if not required else round((len(matched) / len(required)) * 100)
    return ATSMatchResult(score=score, category=category, required_skills=required, matched_skills=matched, missing_skills=missing)

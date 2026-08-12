from dataclasses import dataclass

from automation.tailoring import BASE_SKILLS, SEMANTIC_SKILL_GROUPS, classify_job, extract_keywords
from core.models import Job


@dataclass(frozen=True, slots=True)
class ATSMatchResult:
    score: int
    category: str
    required_skills: tuple[str, ...]
    matched_skills: tuple[str, ...]
    missing_skills: tuple[str, ...]


def verified_skill_set(category: str) -> set[str]:
    """Return only skills supported by the verified profile evidence."""
    verified = set()
    for skill in BASE_SKILLS.get(category, ()):
        lowered = skill.lower()
        for canonical, variants in SEMANTIC_SKILL_GROUPS.items():
            if canonical in lowered or any(variant in lowered for variant in variants):
                verified.add(canonical)
    verified.update({
        "recruitment", "onboarding", "employee relations", "human resources",
        "records management", "reporting", "scheduling", "compliance",
        "legal research", "contract management", "policy", "client communication",
        "documentation", "calendar management", "executive support",
    })
    return verified


def verified_job_keywords(job: Job) -> tuple[str, ...]:
    """Return job requirements that are both detected and supported by verified evidence."""
    category = classify_job(job)
    verified = verified_skill_set(category)
    return tuple(skill for skill in extract_keywords(job) if skill in verified)


def analyse_ats_match(job: Job) -> ATSMatchResult:
    """Score semantic ATS skill coverage without inventing unsupported qualifications."""
    category = classify_job(job)
    required = extract_keywords(job)
    verified = verified_skill_set(category)
    matched = tuple(skill for skill in required if skill in verified)
    missing = tuple(skill for skill in required if skill not in verified)
    score = 100 if not required else round((len(matched) / len(required)) * 100)
    return ATSMatchResult(score=score, category=category, required_skills=required, matched_skills=matched, missing_skills=missing)

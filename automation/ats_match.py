from dataclasses import dataclass

from automation.claims_ledger import verified_skill_keys
from automation.evidence_manifest import build_evidence_manifest, grounded_keywords
from automation.tailoring import classify_job
from core.models import Job


@dataclass(frozen=True, slots=True)
class ATSMatchResult:
    score: int
    category: str
    required_skills: tuple[str, ...]
    matched_skills: tuple[str, ...]
    missing_skills: tuple[str, ...]
    evidence_precision: float = 1.0


def verified_skill_set(category: str) -> set[str]:
    """Return only skills backed by verified applicant evidence."""
    del category
    return verified_skill_keys()


def verified_job_keywords(job: Job) -> tuple[str, ...]:
    """Return vacancy requirements that have concrete applicant evidence."""
    return grounded_keywords(job)


def analyse_ats_match(job: Job) -> ATSMatchResult:
    """Score vacancy coverage and retain an auditable requirement to evidence map."""
    category = classify_job(job)
    manifest = build_evidence_manifest(job)
    required = tuple(item.requirement for item in manifest.requirements)
    matched = tuple(item.requirement for item in manifest.supported)
    missing = tuple(item.requirement for item in manifest.unsupported)
    score = round(manifest.coverage * 100)
    return ATSMatchResult(
        score=score,
        category=category,
        required_skills=required,
        matched_skills=matched,
        missing_skills=missing,
        evidence_precision=manifest.precision,
    )

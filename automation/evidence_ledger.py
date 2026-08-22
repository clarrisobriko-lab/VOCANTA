from __future__ import annotations

from dataclasses import dataclass

from automation.profile import ApplicantProfile


@dataclass(frozen=True, slots=True)
class EvidenceClaim:
    key: str
    claim: str
    evidence: str
    source: str


def build_evidence_ledger(profile: ApplicantProfile) -> tuple[EvidenceClaim, ...]:
    """Build applicant claims exclusively from approved profile and CV facts."""
    claims: list[EvidenceClaim] = []
    for index, record in enumerate(profile.employment_history):
        title = (record.title or "").strip()
        employer = (record.employer or "").strip()
        summary = (record.summary or "").strip()
        if title:
            claims.append(EvidenceClaim(f"employment.{index}.title", title, title, "cv.employment"))
        if employer:
            claims.append(EvidenceClaim(f"employment.{index}.employer", employer, employer, "cv.employment"))
        if summary:
            claims.append(EvidenceClaim(f"employment.{index}.summary", summary, summary, "cv.employment"))
    education = profile.highest_education
    for key, value in (("degree", education.degree), ("discipline", education.discipline), ("institution", education.institution), ("graduation_year", education.graduation_year)):
        value = (value or "").strip()
        if value:
            claims.append(EvidenceClaim(f"education.{key}", value, value, "cv.education"))
    return tuple(claims)


def evidence_text(profile: ApplicantProfile) -> str:
    return " ".join(claim.evidence for claim in build_evidence_ledger(profile)).lower()


def claim_supported(text: str, profile: ApplicantProfile) -> bool:
    """Conservative support check for generated factual fragments.

    Exact or contained facts pass. Novel factual claims do not. This is intended
    as a guardrail, not as a semantic inference engine.
    """
    candidate = " ".join((text or "").lower().split())
    if not candidate:
        return False
    ledger = evidence_text(profile)
    return candidate in ledger or any(candidate in claim.evidence.lower() for claim in build_evidence_ledger(profile))

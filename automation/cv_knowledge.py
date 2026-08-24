from __future__ import annotations

from dataclasses import dataclass
import re

from automation.candidate_knowledge import load_candidate_knowledge
from automation.profile import ApplicantProfile


@dataclass(frozen=True, slots=True)
class GroundedAnswer:
    value: str
    source: str
    confidence: float


def _norm(value: str) -> str:
    return " ".join((value or "").strip().split())


def answer_from_cv(question: str, profile: ApplicantProfile, job_context: str = "") -> GroundedAnswer | None:
    """Resolve application answers from the candidate CV first.

    Structured profile fields supplement the CV where necessary. Vacancy text is
    used only to rank verified evidence and can never create applicant facts.
    """
    q = _norm(question).lower()
    education = profile.highest_education

    if any(key in q for key in ("field of study", "discipline", "major")) and education.discipline:
        return GroundedAnswer(_norm(education.discipline), "profile.education.discipline", 1.0)
    if any(key in q for key in ("highest education", "highest qualification", "education level")):
        value = ", ".join(x for x in (education.degree, education.institution, education.graduation_year) if _norm(x))
        return GroundedAnswer(value, "profile.education", 1.0) if value else None
    if "number of employers" in q or "how many companies have you worked for" in q:
        if profile.number_of_employers:
            return GroundedAnswer(_norm(profile.number_of_employers), "profile.employment.count", 1.0)
    if any(key in q for key in ("nationality", "citizenship")) and profile.nationality:
        return GroundedAnswer(_norm(profile.nationality), "profile.nationality", 1.0)
    if re.search(r"\b(country of residence|where are you based|currently work|current country)\b", q) and profile.country:
        return GroundedAnswer(_norm(profile.country), "profile.country", 1.0)

    knowledge = load_candidate_knowledge(profile)
    narrative = knowledge.narrative(question, job_context=job_context)
    if narrative:
        ranked = knowledge.rank(question, job_context=job_context, limit=1)
        source = ranked[0].source if ranked else "cv.semantic"
        return GroundedAnswer(narrative, source, 0.95)
    return None

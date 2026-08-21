from __future__ import annotations

from dataclasses import dataclass
import re
from typing import Iterable

from automation.profile import ApplicantProfile, EmploymentRecord


@dataclass(frozen=True, slots=True)
class GroundedAnswer:
    value: str
    source: str
    confidence: float


def _norm(value: str) -> str:
    return " ".join((value or "").strip().split())


def _employment_text(records: Iterable[EmploymentRecord]) -> str:
    parts: list[str] = []
    for record in records:
        row = ", ".join(x for x in (_norm(record.title), _norm(record.employer)) if x)
        dates = " to ".join(x for x in (_norm(record.start_year), "Present" if record.current else _norm(record.end_year)) if x)
        if dates:
            row = f"{row} ({dates})"
        if record.summary:
            row = f"{row}. {_norm(record.summary)}"
        if row:
            parts.append(row)
    return " ".join(parts)


def answer_from_cv(question: str, profile: ApplicantProfile) -> GroundedAnswer | None:
    """Return only answers grounded in approved structured CV/profile facts.

    This intentionally refuses to infer facts that are not represented in the
    applicant profile. Missing facts remain manual rather than hallucinated.
    """
    q = _norm(question).lower()
    education = profile.highest_education
    employment = profile.employment_history

    if any(key in q for key in ("highest education", "highest qualification", "degree", "education level")):
        value = ", ".join(x for x in (education.degree, education.institution, education.graduation_year) if _norm(x))
        return GroundedAnswer(value, "cv.education", 1.0) if value else None

    if any(key in q for key in ("field of study", "discipline", "major")) and education.discipline:
        return GroundedAnswer(_norm(education.discipline), "cv.education.discipline", 1.0)

    if any(key in q for key in ("current job title", "current role", "present role")):
        current = next((item for item in employment if item.current), employment[0] if employment else None)
        if current and current.title:
            return GroundedAnswer(_norm(current.title), "cv.employment.current.title", 1.0)

    if any(key in q for key in ("current employer", "present employer")):
        current = next((item for item in employment if item.current), None)
        if current and current.employer:
            return GroundedAnswer(_norm(current.employer), "cv.employment.current.employer", 1.0)

    if any(key in q for key in ("employment history", "work history", "professional experience", "relevant experience", "tell us about your experience")):
        value = _employment_text(employment)
        if value:
            return GroundedAnswer(value[:1800], "cv.employment", 0.95)

    if "number of employers" in q and profile.number_of_employers:
        return GroundedAnswer(_norm(profile.number_of_employers), "cv.employment.count", 1.0)

    if any(key in q for key in ("nationality", "citizenship")) and profile.nationality:
        return GroundedAnswer(_norm(profile.nationality), "profile.nationality", 1.0)

    if re.search(r"\b(location|country of residence|where are you based)\b", q) and profile.country:
        return GroundedAnswer(_norm(profile.country), "profile.country", 1.0)

    return None

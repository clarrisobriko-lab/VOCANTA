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


def _tokens(value: str) -> set[str]:
    stop = {"the","and","for","with","your","you","our","this","that","are","was","have","has","job","role","work","experience","relevant","describe","tell","about","please","candidate","position","will","from","their","they","who","what","how"}
    return {word for word in re.findall(r"[a-zA-Z]{3,}", (value or "").lower()) if word not in stop}


def _record_text(record: EmploymentRecord) -> str:
    row = ", ".join(x for x in (_norm(record.title), _norm(record.employer)) if x)
    dates = " to ".join(x for x in (_norm(record.start_year), "Present" if record.current else _norm(record.end_year)) if x)
    if dates: row = f"{row} ({dates})"
    if record.summary: row = f"{row}. {_norm(record.summary)}"
    return row


def _ranked_employment(question: str, records: Iterable[EmploymentRecord], job_context: str = "") -> list[EmploymentRecord]:
    question_tokens = _tokens(question)
    job_tokens = _tokens(job_context)
    scored = []
    for position, record in enumerate(records):
        haystack = _tokens(f"{record.title} {record.employer} {record.summary}")
        question_overlap = len(question_tokens & haystack)
        vacancy_overlap = len(job_tokens & haystack)
        current_bonus = 0.25 if record.current else 0.0
        score = (question_overlap * 2.0) + vacancy_overlap + current_bonus
        scored.append((score, -position, record))
    scored.sort(key=lambda item: (item[0], item[1]), reverse=True)
    return [item[2] for item in scored]


def _employment_text(records: Iterable[EmploymentRecord], limit: int = 1800) -> str:
    parts = [_record_text(record) for record in records]
    return " ".join(part for part in parts if part)[:limit]


def answer_from_cv(question: str, profile: ApplicantProfile, job_context: str = "") -> GroundedAnswer | None:
    """Answer only from approved CV/profile facts.

    For experience questions, rank evidence against both the employer's question
    and vacancy context. Job text influences ordering only and can never become
    an applicant fact.
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
        if current and current.title: return GroundedAnswer(_norm(current.title), "cv.employment.current.title", 1.0)
    if any(key in q for key in ("current employer", "present employer")):
        current = next((item for item in employment if item.current), None)
        if current and current.employer: return GroundedAnswer(_norm(current.employer), "cv.employment.current.employer", 1.0)
    if any(key in q for key in ("employment history", "work history", "professional experience", "relevant experience", "tell us about your experience", "background", "skills and experience")):
        ranked = _ranked_employment(question, employment, job_context)
        value = _employment_text(ranked)
        if value:
            source = "cv.employment.question_and_vacancy_ranked" if job_context else "cv.employment.relevance_ranked"
            return GroundedAnswer(value, source, 0.95)
    if "number of employers" in q and profile.number_of_employers:
        return GroundedAnswer(_norm(profile.number_of_employers), "cv.employment.count", 1.0)
    if any(key in q for key in ("nationality", "citizenship")) and profile.nationality:
        return GroundedAnswer(_norm(profile.nationality), "profile.nationality", 1.0)
    if re.search(r"\b(location|country of residence|where are you based)\b", q) and profile.country:
        return GroundedAnswer(_norm(profile.country), "profile.country", 1.0)
    return None

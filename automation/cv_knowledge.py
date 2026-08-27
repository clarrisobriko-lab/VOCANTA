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


def _tokens(value: str) -> set[str]:
    stop = {"the", "and", "for", "with", "your", "you", "our", "this", "that", "are", "was", "have", "has", "had", "job", "role", "work", "experience", "describe", "relevant", "professional", "please"}
    return {token for token in re.findall(r"[a-z0-9]+", (value or "").lower()) if len(token) > 2 and token not in stop}


def _employment_text(item) -> str:
    dates = " to ".join(part for part in (item.start_year, "Present" if item.current else item.end_year) if part)
    head = ", ".join(part for part in (item.title, item.employer, dates) if part)
    return f"{head}. {item.summary}".strip() if item.summary else head


def _ranked_employment(profile: ApplicantProfile, question: str, job_context: str) -> list:
    target = _tokens(f"{question} {job_context}")
    indexed = list(enumerate(profile.employment_history))
    def score(pair):
        index, item = pair
        overlap = len(target & _tokens(_employment_text(item)))
        return (-overlap, index)
    indexed.sort(key=score)
    return [item for _, item in indexed]


def answer_from_cv(question: str, profile: ApplicantProfile, job_context: str = "") -> GroundedAnswer | None:
    """Resolve application answers only from verified candidate evidence.

    The CV and its structured candidate facts are evidence. Vacancy text may
    rank that evidence, but it can never create a candidate fact.
    """
    q = _norm(question).lower()
    education = profile.highest_education

    # Questions asking for assessed performance or results require an explicit
    # verified result. A degree, institution or unrelated CV sentence is not
    # evidence of school performance.
    if ("high school" in q or "secondary school" in q) and any(key in q for key in ("perform", "performance", "result", "score", "grade", "ranking", "mathematics", "native language")):
        return None

    if any(key in q for key in ("current job title", "current role", "present job title", "present role")):
        current = next((item for item in profile.employment_history if item.current), None)
        if current and current.title:
            return GroundedAnswer(_norm(current.title), "cv.employment.current.title", 1.0)

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
    if re.search(r"\b(country of residence|where are you based|currently work|current country|location)\b", q) and profile.country:
        return GroundedAnswer(_norm(profile.country), "profile.country", 1.0)

    # Broad relevant experience questions need a complete factual employment
    # answer. Rank records for the vacancy, but retain every verified record so
    # relevant history is not silently discarded merely because keyword overlap
    # is zero.
    if "relevant" in q and "experience" in q and profile.employment_history:
        records = _ranked_employment(profile, question, job_context)
        value = " ".join(filter(None, (_employment_text(item) for item in records)))
        if value:
            return GroundedAnswer(value, "cv.employment.question_and_vacancy_ranked", 0.95)

    knowledge = load_candidate_knowledge(profile)
    narrative = knowledge.narrative(question, job_context=job_context)
    if narrative:
        ranked = knowledge.rank(question, job_context=job_context, limit=1)
        source = ranked[0].source if ranked else "cv.semantic"
        return GroundedAnswer(narrative, source, 0.95)
    return None

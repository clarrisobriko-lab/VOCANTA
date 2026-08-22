from __future__ import annotations

from dataclasses import dataclass
import re

from automation.cv_knowledge import answer_from_cv
from automation.profile import ApplicantProfile
from automation.questions import identify_intent, resolve_question


@dataclass(frozen=True, slots=True)
class SemanticAnswer:
    value: str
    source: str
    confidence: float


def _norm(text: str | None) -> str:
    return " ".join((text or "").strip().split())


def _clean(text: str) -> str:
    # Applicant prose must not contain dash punctuation.
    return re.sub(r"[\u2013\u2014]", ",", _norm(text))


def _ranked_experience(question: str, profile: ApplicantProfile, job_context: str) -> SemanticAnswer | None:
    grounded = answer_from_cv(question, profile, job_context=job_context)
    if grounded and grounded.value:
        return SemanticAnswer(_clean(grounded.value), grounded.source, grounded.confidence)
    return None


def answer_application_question(question: str, profile: ApplicantProfile, *, job_context: str = "") -> SemanticAnswer | None:
    """Resolve an application question from verified applicant evidence only.

    Vacancy text may rank evidence, but it can never become an applicant fact.
    Unknown facts remain unanswered.
    """
    q = _norm(question).lower()

    resolution = resolve_question(question, profile)
    if resolution.value and resolution.auto_fill_allowed:
        return SemanticAnswer(_clean(resolution.value), f"profile.{resolution.intent.value.lower()}", resolution.confidence / 100)

    if "bachelor" in q and any(k in q for k in ("result", "grading", "grade", "gpa")):
        for key, value in profile.standard_answers.items():
            key_l = key.lower()
            if "bachelor" in key_l and any(k in key_l for k in ("result", "grading", "grade", "gpa")) and value:
                return SemanticAnswer(_clean(value), "profile.standard_answers.degree_result", 1.0)
        return None

    if any(k in q for k in ("administration", "executive support", "logistics", "events", "travel management")):
        return _ranked_experience(question, profile, job_context)

    if any(k in q for k in ("take responsibility", "responsibility for something important", "large amount of detail", "high accuracy", "accuracy", "challenge")):
        return _ranked_experience(question, profile, job_context)

    if any(k in q for k in ("experience", "background", "skills", "describe a case", "describe an occasion")):
        return _ranked_experience(question, profile, job_context)

    grounded = answer_from_cv(question, profile, job_context=job_context)
    if grounded and grounded.value:
        return SemanticAnswer(_clean(grounded.value), grounded.source, grounded.confidence)
    return None

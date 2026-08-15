from __future__ import annotations

import re
from dataclasses import dataclass
from urllib.parse import urlparse

from core.models import Job


SKILL_PATTERNS = {
    "calendar management": ("calendar", "diary management", "scheduling"),
    "executive support": ("executive support", "executive assistant", "c-suite"),
    "human resources": ("human resources", "hr operations", "people operations"),
    "recruitment": ("recruitment", "recruiting", "talent acquisition"),
    "onboarding": ("onboarding", "induction"),
    "compliance": ("compliance", "regulatory"),
    "contracts": ("contract management", "contract review", "contracts"),
    "legal research": ("legal research", "legal analysis"),
    "stakeholder management": ("stakeholder", "relationship management"),
    "project coordination": ("project coordination", "project management"),
    "microsoft office": ("microsoft office", "microsoft 365", "office 365"),
    "google workspace": ("google workspace", "g suite"),
    "slack": ("slack",),
    "zoom": ("zoom", "video conferencing"),
    "salesforce": ("salesforce",),
    "workday": ("workday",),
}

INTERVIEW_SIGNALS = {
    "Tell me about your experience with {skill}.",
    "Describe a situation where you used {skill} to solve a problem.",
}


@dataclass(frozen=True, slots=True)
class JobIntelligence:
    employer: str
    employer_domain: str
    skills: tuple[str, ...]
    likely_interview_questions: tuple[str, ...]
    salary_text: str
    remote_signal: str


def _text(job: Job) -> str:
    return f"{job.title} {job.description} {job.location} {job.salary}".lower()


def detect_skills(job: Job) -> tuple[str, ...]:
    text = _text(job)
    return tuple(skill for skill, patterns in SKILL_PATTERNS.items() if any(pattern in text for pattern in patterns))


def predict_interview_questions(job: Job, limit: int = 6) -> tuple[str, ...]:
    skills = detect_skills(job)
    questions: list[str] = []
    for skill in skills:
        questions.append(f"Tell me about your experience with {skill}.")
        if len(questions) >= limit:
            break
    if len(questions) < limit:
        questions.append(f"Why are you interested in the {job.title} role at {job.company}?")
    return tuple(questions[:limit])


def extract_salary_text(job: Job) -> str:
    if job.salary and job.salary.strip():
        return job.salary.strip()
    match = re.search(r"(?:£|\$|€|₦)\s?[\d,.]+(?:\s*[-–]\s*(?:£|\$|€|₦)?\s?[\d,.]+)?(?:\s*(?:per|/)?\s*(?:year|month|hour|annum|yr|mo|hr))?", job.description, re.I)
    return match.group(0).strip() if match else ""


def analyse_job(job: Job) -> JobIntelligence:
    host = (urlparse(job.url).hostname or "").lower().removeprefix("www.")
    text = _text(job)
    if any(term in text for term in ("worldwide", "anywhere", "global", "international")):
        remote = "GLOBAL_REMOTE"
    elif "remote" in text:
        remote = "REMOTE"
    else:
        remote = "ONSITE_OR_UNCLEAR"
    return JobIntelligence(
        employer=job.company,
        employer_domain=host,
        skills=detect_skills(job),
        likely_interview_questions=predict_interview_questions(job),
        salary_text=extract_salary_text(job),
        remote_signal=remote,
    )

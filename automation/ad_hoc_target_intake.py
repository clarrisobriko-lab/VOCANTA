from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class IntakeStatus(str, Enum):
    NEEDS_SOURCE_VERIFICATION = "NEEDS_SOURCE_VERIFICATION"
    READY_FOR_EVIDENCE_MATCH = "READY_FOR_EVIDENCE_MATCH"
    BLOCKED = "BLOCKED"


@dataclass(frozen=True, slots=True)
class AdHocVacancy:
    employer: str
    title: str
    location: str
    work_pattern: str
    compensation: str
    responsibilities: tuple[str, ...]
    source_url: str = ""
    application_url: str = ""
    deadline: str = ""


@dataclass(frozen=True, slots=True)
class IntakeResult:
    status: IntakeStatus
    vacancy: AdHocVacancy
    required_verifications: tuple[str, ...]


def intake(vacancy: AdHocVacancy) -> IntakeResult:
    if not vacancy.employer.strip() or not vacancy.title.strip():
        return IntakeResult(IntakeStatus.BLOCKED, vacancy, ("employer and title",))

    missing = []
    if not vacancy.source_url.strip():
        missing.append("official or attributable vacancy source")
    if not vacancy.application_url.strip():
        missing.append("verified application channel")
    if not vacancy.deadline.strip():
        missing.append("current vacancy status or deadline")

    if missing:
        return IntakeResult(IntakeStatus.NEEDS_SOURCE_VERIFICATION, vacancy, tuple(missing))
    return IntakeResult(IntakeStatus.READY_FOR_EVIDENCE_MATCH, vacancy, ())


WOMEN_ON_TOP_EXECUTIVE_ASSISTANT = AdHocVacancy(
    employer="Women on Top",
    title="Executive Assistant",
    location="Remote",
    work_pattern="Part-time, once or twice a week",
    compensation="GBP 200/day",
    responsibilities=(
        "Manage and maintain Beer Unlocked bursary scheme administration",
        "Support Google Drive organisation and upkeep",
        "Keep sponsor packs current and easy to locate",
        "Update website content in Squarespace",
        "Maintain the main projects and contacts dashboard in Excel",
        "Manage email, calendar, calls and meetings",
        "Use Excel and Google Sheets at an advanced level",
    ),
)

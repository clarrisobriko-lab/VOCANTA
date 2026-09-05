from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
import re

from automation.profile import ApplicantProfile


@dataclass(frozen=True, slots=True)
class ResolvedField:
    value: str
    source: str


def _normalize(text: str | None) -> str:
    cleaned = re.sub(r"[_\-]+", " ", (text or "").lower())
    return " ".join(cleaned.split())


class FormProfileResolver:
    """Resolve repeated application form fields from structured profile data.

    Application forms commonly repeat generic labels such as Company, Job title,
    Start year and End year. Those labels cannot be resolved correctly as global
    profile attributes. This resolver assigns each occurrence to the matching
    employment record in profile order, which mirrors CV parsing in Easy Apply.
    """

    EMPLOYMENT_ALIASES = {
        "employer": ("employer", "company", "company name", "organisation", "organization", "employer name"),
        "title": ("job title", "position", "position title", "role", "role title", "title"),
        "start_year": ("start year", "year started", "employment start year", "from year"),
        "end_year": ("end year", "year ended", "employment end year", "to year"),
        "summary": ("responsibilities", "job description", "role description", "employment summary", "duties", "description of duties"),
    }

    EDUCATION_ALIASES = {
        "institution": ("university", "institution", "school", "school name", "college"),
        "degree": ("degree", "qualification", "highest qualification"),
        "discipline": ("field of study", "discipline", "major", "course of study"),
        "graduation_year": ("graduation year", "year graduated", "completion year"),
        "country": ("education country", "country of institution", "country of study"),
    }

    def __init__(self, profile: ApplicantProfile):
        self.profile = profile
        self._employment_occurrences: dict[str, int] = defaultdict(int)

    @staticmethod
    def _matches(label: str, aliases: tuple[str, ...]) -> bool:
        normalized = _normalize(label)
        return any(alias == normalized or alias in normalized for alias in aliases)

    def _employment_kind(self, label: str) -> str:
        normalized = _normalize(label)
        if any(term in normalized for term in ("education", "school", "university", "degree", "qualification")):
            return ""
        for kind, aliases in self.EMPLOYMENT_ALIASES.items():
            if self._matches(normalized, aliases):
                return kind
        return ""

    def _education_kind(self, label: str) -> str:
        normalized = _normalize(label)
        for kind, aliases in self.EDUCATION_ALIASES.items():
            if self._matches(normalized, aliases):
                return kind
        return ""

    def resolve(self, label: str) -> ResolvedField | None:
        employment_kind = self._employment_kind(label)
        if employment_kind:
            index = self._employment_occurrences[employment_kind]
            self._employment_occurrences[employment_kind] += 1
            if index >= len(self.profile.employment_history):
                return None
            record = self.profile.employment_history[index]
            value = str(getattr(record, employment_kind, "") or "").strip()
            if employment_kind == "end_year" and record.current and not value:
                return None
            if not value:
                return None
            return ResolvedField(value, f"profile.employment_history[{index}].{employment_kind}")

        education_kind = self._education_kind(label)
        if education_kind:
            value = str(getattr(self.profile.highest_education, education_kind, "") or "").strip()
            if not value:
                return None
            return ResolvedField(value, f"profile.highest_education.{education_kind}")

        return None

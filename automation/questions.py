from dataclasses import dataclass
from enum import Enum
import re

from automation.profile import ApplicantProfile


class Intent(str, Enum):
    UNKNOWN = "UNKNOWN"
    FIRST_NAME = "FIRST_NAME"; MIDDLE_NAME = "MIDDLE_NAME"; LAST_NAME = "LAST_NAME"; FULL_NAME = "FULL_NAME"
    EMAIL = "EMAIL"; PHONE = "PHONE"; CITY = "CITY"; CURRENT_COUNTRY = "CURRENT_COUNTRY"; NATIONALITY = "NATIONALITY"; REGION = "REGION"
    ADDRESS = "ADDRESS"; POSTAL_CODE = "POSTAL_CODE"; LINKEDIN = "LINKEDIN"; WEBSITE = "WEBSITE"
    UNIVERSITY = "UNIVERSITY"; DEGREE = "DEGREE"; DISCIPLINE = "DISCIPLINE"; GRADUATION_YEAR = "GRADUATION_YEAR"
    SPONSORSHIP = "SPONSORSHIP"; WORK_AUTHORIZATION = "WORK_AUTHORIZATION"; RELOCATION = "RELOCATION"; REMOTE_PREFERENCE = "REMOTE_PREFERENCE"
    TRAVEL = "TRAVEL"; EMPLOYER_COUNT = "EMPLOYER_COUNT"; NOTICE_PERIOD = "NOTICE_PERIOD"; SALARY = "SALARY"
    PRIVACY_ACKNOWLEDGEMENT = "PRIVACY_ACKNOWLEDGEMENT"; DEMOGRAPHIC = "DEMOGRAPHIC"; WRITTEN_RESPONSE = "WRITTEN_RESPONSE"


@dataclass(frozen=True, slots=True)
class QuestionResolution:
    intent: Intent
    value: str
    confidence: int
    auto_fill_allowed: bool
    reason: str = ""


RESTRICTION_PATTERNS = (
    r"use only (?:your|my) own words", r"do not use (?:ai|artificial intelligence|chatgpt)",
    r"(?:ai|artificial intelligence)[ -]generated (?:content|answer|response)s? (?:is|are) prohibited",
    r"personally authored", r"without (?:ai|automated) assistance", r"certify that .* (?:my own|your own) work",
)

INTENT_ALIASES: tuple[tuple[Intent, tuple[str, ...]], ...] = (
    (Intent.FIRST_NAME, ("first name", "given name")), (Intent.MIDDLE_NAME, ("middle name", "middle initial")),
    (Intent.LAST_NAME, ("last name", "surname", "family name")), (Intent.FULL_NAME, ("full name", "candidate name", "your name")),
    (Intent.EMAIL, ("email", "e mail")), (Intent.PHONE, ("phone", "mobile", "telephone", "contact number")),
    (Intent.CURRENT_COUNTRY, ("current country", "country of residence", "where are you currently based", "in which country do you currently work")),
    (Intent.NATIONALITY, ("nationality", "citizenship", "citizen of")), (Intent.REGION, ("region", "geographic region")),
    (Intent.CITY, ("current city", "city", "location")), (Intent.ADDRESS, ("street address", "home address", "address")),
    (Intent.POSTAL_CODE, ("postal code", "postcode", "zip code")), (Intent.LINKEDIN, ("linkedin",)),
    (Intent.WEBSITE, ("portfolio", "personal website", "website")), (Intent.UNIVERSITY, ("university", "institution", "school attended", "education school")),
    (Intent.DEGREE, ("degree", "highest qualification", "education level")), (Intent.DISCIPLINE, ("discipline", "field of study", "major", "course of study")),
    (Intent.GRADUATION_YEAR, ("graduation year", "year graduated", "completion year")), (Intent.SPONSORSHIP, ("require sponsorship", "visa sponsorship", "sponsorship")),
    (Intent.WORK_AUTHORIZATION, ("work authorization", "work authorisation", "legally authorised", "legally authorized", "authorised to work", "authorized to work", "eligible to work")),
    (Intent.RELOCATION, ("relocate", "relocation")), (Intent.REMOTE_PREFERENCE, ("remote preference", "remote work")),
    (Intent.TRAVEL, ("travel commitment", "willing to travel", "international travel", "able to commit to this")),
    (Intent.EMPLOYER_COUNT, ("number of employers", "how many employers", "previous employers", "how many companies have you worked for")),
    (Intent.NOTICE_PERIOD, ("notice period", "when can you start", "availability")),
    (Intent.SALARY, ("salary expectation", "expected salary", "desired salary", "compensation expectation")),
    (Intent.PRIVACY_ACKNOWLEDGEMENT, ("privacy notice", "privacy policy", "data processing", "acknowledge", "read and agree")),
)

DEMOGRAPHIC_TERMS = ("gender", "race", "ethnicity", "disability", "veteran", "sexual orientation", "religion", "age range")


def normalize(text: str | None) -> str:
    cleaned = re.sub(r"[_\-]+", " ", (text or "").lower())
    return " ".join(cleaned.split())


def _tokens(text: str) -> set[str]:
    return {token for token in re.findall(r"[a-z0-9]+", normalize(text)) if len(token) > 2}


def restriction_reason(text: str) -> str:
    normalized = normalize(text)
    for pattern in RESTRICTION_PATTERNS:
        if re.search(pattern, normalized, flags=re.IGNORECASE):
            return f"Employer declaration requires candidate review and a personally authored response: {normalized[:220]}"
    return ""


def identify_intent(label: str) -> Intent:
    normalized = normalize(label)
    if normalized == "school": return Intent.UNIVERSITY
    if normalized == "degree": return Intent.DEGREE
    if normalized == "discipline": return Intent.DISCIPLINE
    if normalized in {"country", "country / region", "country region", "country or region", "current location country"}: return Intent.CURRENT_COUNTRY
    if any(term in normalized for term in DEMOGRAPHIC_TERMS): return Intent.DEMOGRAPHIC
    for intent, aliases in INTENT_ALIASES:
        if any(alias == normalized or alias in normalized for alias in aliases): return intent
    if any(term in normalized for term in ("why", "describe", "explain", "tell us", "motivation", "cover letter", "occasion", "case where")): return Intent.WRITTEN_RESPONSE
    return Intent.UNKNOWN


def _dynamic_standard_answer(label: str, answers: dict[str, str]) -> tuple[str, int]:
    target = _tokens(label)
    if not target: return "", 0
    best_value, best_score = "", 0
    for stored_label, value in answers.items():
        if not value: continue
        candidate = _tokens(stored_label)
        if not candidate: continue
        overlap = len(target & candidate); score = round(100 * overlap / max(len(target), len(candidate)))
        if score > best_score: best_value, best_score = value, score
    return (best_value, best_score) if best_score >= 60 else ("", best_score)


def resolve_question(label: str, profile: ApplicantProfile, *, has_middle_name_field: bool = True) -> QuestionResolution:
    restriction = restriction_reason(label); intent = identify_intent(label)
    if restriction: return QuestionResolution(intent, "", 100, False, restriction)
    values = {
        Intent.FIRST_NAME: profile.first_name, Intent.MIDDLE_NAME: profile.middle_name,
        Intent.LAST_NAME: profile.last_name if has_middle_name_field else profile.employer_last_name,
        Intent.FULL_NAME: profile.full_name, Intent.EMAIL: profile.email, Intent.PHONE: profile.phone,
        Intent.CITY: profile.city, Intent.CURRENT_COUNTRY: profile.country, Intent.NATIONALITY: profile.nationality,
        Intent.REGION: profile.region, Intent.ADDRESS: profile.address, Intent.POSTAL_CODE: profile.postal_code,
        Intent.LINKEDIN: profile.linkedin_url, Intent.WEBSITE: profile.website_url,
        Intent.UNIVERSITY: profile.highest_education.institution, Intent.DEGREE: profile.highest_education.degree,
        Intent.DISCIPLINE: profile.highest_education.discipline, Intent.GRADUATION_YEAR: profile.highest_education.graduation_year,
        Intent.SPONSORSHIP: "Yes" if profile.requires_sponsorship else "No", Intent.WORK_AUTHORIZATION: profile.work_authorization,
        Intent.RELOCATION: "Yes" if profile.open_to_relocation else "No", Intent.REMOTE_PREFERENCE: profile.remote_preference,
        Intent.TRAVEL: profile.travel_commitment, Intent.EMPLOYER_COUNT: profile.number_of_employers,
        Intent.NOTICE_PERIOD: profile.notice_period, Intent.SALARY: profile.salary_expectation,
        Intent.PRIVACY_ACKNOWLEDGEMENT: "Yes" if profile.privacy_acknowledgements else "",
    }
    if intent == Intent.DEMOGRAPHIC:
        if not profile.auto_fill_demographics: return QuestionResolution(intent, "", 100, False, "Optional demographic fields are disabled")
        for key, value in profile.demographics.items():
            if key.lower() in normalize(label): return QuestionResolution(intent, value, 90, True)
        return QuestionResolution(intent, "", 50, False, "No stored demographic answer")
    exact = profile.standard_answers.get(normalize(label), "")
    if exact: return QuestionResolution(intent, exact, 100, True, "Exact approved answer")
    dynamic, confidence = _dynamic_standard_answer(label, profile.standard_answers)
    if dynamic: return QuestionResolution(intent, dynamic, confidence, True, "Matched approved answer semantically")
    value = str(values.get(intent, "") or "")
    allowed = bool(value) and intent not in {Intent.UNKNOWN, Intent.WRITTEN_RESPONSE}
    return QuestionResolution(intent, value, 95 if allowed else 30, allowed, "" if allowed else "No approved structured answer")

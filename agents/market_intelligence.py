from dataclasses import dataclass

from config.settings import (
    COUNTRY_ALIASES,
    COUNTRY_LANGUAGE_PENALTIES,
    COUNTRY_PRIORITY,
    ENGLISH_WORKING_LANGUAGE_TERMS,
    EXPLICIT_ONSITE_TERMS,
    GLOBAL_REMOTE_TERMS,
    REGIONAL_REMOTE_TERMS,
    SECONDARY_COUNTRY_PRIORITY,
)
from core.models import Job
from core.text_rules import contains_any, contains_term


@dataclass(frozen=True, slots=True)
class MarketAssessment:
    country: str | None
    market_score: int
    language_penalty: int
    global_remote: bool
    supported: bool


def _combined_text(job: Job) -> str:
    return " ".join(
        (
            job.company,
            job.title,
            job.location,
            job.description,
            job.employment_type,
        )
    ).lower()


def detect_country(job: Job) -> str | None:
    location = job.location.lower()
    for country, aliases in COUNTRY_ALIASES.items():
        if any(contains_term(location, alias) for alias in aliases):
            return country
    return None


def assess_market(job: Job) -> MarketAssessment:
    text = _combined_text(job)
    location = job.location.lower()

    country = detect_country(job)
    explicit_onsite = contains_any(location, EXPLICIT_ONSITE_TERMS) or contains_any(text, EXPLICIT_ONSITE_TERMS)

    # A concrete office location takes precedence over generic company language such as
    # "global company" or "global distributed collaboration". Worldwide eligibility is
    # accepted only when the vacancy itself uses an explicit remote-worldwide phrase.
    location_global_remote = contains_any(location, GLOBAL_REMOTE_TERMS)
    text_global_remote = contains_any(text, GLOBAL_REMOTE_TERMS)
    global_remote = (location_global_remote or text_global_remote) and not explicit_onsite and country is None

    if global_remote:
        return MarketAssessment(
            country=None,
            market_score=100,
            language_penalty=0,
            global_remote=True,
            supported=True,
        )

    if country in COUNTRY_PRIORITY:
        return MarketAssessment(
            country=country,
            market_score=COUNTRY_PRIORITY[country],
            language_penalty=0,
            global_remote=False,
            supported=True,
        )

    if country in SECONDARY_COUNTRY_PRIORITY:
        english_exemption = contains_any(text, ENGLISH_WORKING_LANGUAGE_TERMS)
        penalty = 0 if english_exemption else COUNTRY_LANGUAGE_PENALTIES[country]
        return MarketAssessment(
            country=country,
            market_score=SECONDARY_COUNTRY_PRIORITY[country],
            language_penalty=penalty,
            global_remote=False,
            supported=True,
        )

    regional_remote = contains_any(location, REGIONAL_REMOTE_TERMS)
    if regional_remote:
        return MarketAssessment(
            country=None,
            market_score=72 if "emea" in location else 70,
            language_penalty=0,
            global_remote=False,
            supported=True,
        )

    if not location.strip():
        return MarketAssessment(
            country=None,
            market_score=60,
            language_penalty=0,
            global_remote=False,
            supported=True,
        )

    return MarketAssessment(
        country=country,
        market_score=0,
        language_penalty=0,
        global_remote=False,
        supported=False,
    )

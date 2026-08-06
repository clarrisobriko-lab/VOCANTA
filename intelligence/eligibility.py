from dataclasses import dataclass
import re
from urllib.parse import urlparse

from agents.market_intelligence import assess_market
from config.settings import (
    BLOCKED_AUTOMATION_DOMAINS,
    DISCOVERY_ONLY_AUTOMATION_DOMAINS,
    DISCOVERY_ONLY_COMPANIES,
    DISCOVERY_ONLY_SOURCES,
    BLOCK_SENIOR_TITLES,
    HARD_SENIOR_TITLE_TERMS,
    INTERNATIONAL_OPENNESS_TERMS,
    MAX_AUTOMATION_REQUIRED_YEARS,
    REGION_RESTRICTION_TERMS,
    STRICT_ELIGIBILITY_MODE,
)
from core.models import Job
from core.text_rules import contains_any, matched_terms
from intelligence.ngo import assess_ngo


RULE_VERSION = "2.9.5"

HARD_GEOGRAPHY_RULES = {
    "venezuela only": "Venezuela-only role",
    "united states only": "United States-only role",
    "us only": "United States-only role",
    "usa only": "United States-only role",
    "u.s. only": "United States-only role",
    "canada only": "Canada-only role",
    "australia only": "Australia-only role",
    "new zealand only": "New Zealand-only role",
    "united kingdom only": "United Kingdom-only role",
    "uk only": "United Kingdom-only role",
    "eu only": "European Union-only role",
    "europe only": "Europe-only role",
    "emea only": "EMEA-only role",
    "latam only": "LATAM-only role",
    "eu citizens only": "EU citizenship required",
    "citizens only": "Citizenship restriction",
    "local candidates only": "Local candidates only",
    "anywhere in the united states": "United States-only role",
    "anywhere in the us": "United States-only role",
    "anywhere in usa": "United States-only role",
    "anywhere in canada": "Canada-only role",
    "anywhere in the uk": "United Kingdom-only role",
    "anywhere in europe": "Europe-only role",
    "anywhere in the eu": "European Union-only role",
    "remote within the us": "United States-only role",
    "remote within the uk": "United Kingdom-only role",
    "remote within the eu": "European Union-only role",
    "remote - us": "United States-only role",
    "remote, us": "United States-only role",
    "remote us": "United States-only role",
    "us-based only": "United States-only role",
    "must be based in the us": "United States residence required",
    "must reside in the us": "United States residence required",
    "must be based in": "Existing local residence required",
    "must currently reside in": "Existing local residence required",
    "must already reside in": "Existing local residence required",
    "must already live in": "Existing local residence required",
    "must reside in": "Existing local residence required",
}

LOCAL_LANGUAGE_RULES = {
    "native german required": "Native German required",
    "fluent german required": "Fluent German required",
    "german language required": "German required",
    "german speaker required": "German required",
    "native french required": "Native French required",
    "fluent french required": "Fluent French required",
    "french language required": "French required",
    "french speaker required": "French required",
    "native spanish required": "Native Spanish required",
    "fluent spanish required": "Fluent Spanish required",
    "spanish language required": "Spanish required",
    "spanish speaker required": "Spanish required",
}

NEGATIVE_SPONSORSHIP_RULES = {
    "no sponsorship": -60,
    "no visa sponsorship": -60,
    "visa sponsorship is not available": -60,
    "no sponsorship available": -60,
    "unable to sponsor": -60,
    "cannot sponsor": -60,
    "not eligible for sponsorship": -60,
    "must have the right to work": -45,
    "existing right to work required": -45,
    "work authorization required": -45,
    "work authorisation required": -45,
    "must already have work authorization": -45,
    "must already have work authorisation": -45,
    "must already be authorised to work": -45,
    "must already be authorized to work": -45,
    "authorized to work in the us": -60,
    "authorised to work in the us": -60,
}

POSITIVE_SPONSORSHIP_RULES = {
    "visa sponsorship available": 45,
    "visa sponsorship": 35,
    "work permit support": 35,
    "sponsorship available": 35,
    "immigration support": 30,
    "international applicants encouraged": 25,
    "international candidates welcome": 25,
    "global talent": 15,
}

RELOCATION_RULES = {
    "relocation package": 35,
    "relocation support": 35,
    "relocation assistance": 35,
    "accommodation provided": 25,
    "flight reimbursement": 20,
    "settling-in allowance": 20,
    "global mobility package": 30,
}


@dataclass(frozen=True, slots=True)
class EligibilityDecision:
    verdict: str
    primary_reason: str
    reason_codes: tuple[str, ...]
    evidence: tuple[str, ...]
    confidence: int
    sponsorship_label: str
    sponsorship_score: int
    relocation_label: str
    international_hiring_label: str
    ngo_label: str
    ngo_bonus: int
    market_supported: bool
    market_score: int
    language_penalty: int
    global_remote: bool
    career_level: str = "UNKNOWN"
    required_years: int | None = None
    rule_version: str = RULE_VERSION

    @property
    def blocked(self) -> bool:
        return self.verdict == "BLOCK"

    @property
    def recommendation(self) -> str:
        return {
            "BLOCK": "IGNORE",
            "REVIEW": "RESEARCH",
            "PRIORITY": "PRIORITY",
            "APPLY": "APPLY",
        }[self.verdict]


def _text(job: Job) -> str:
    return " ".join((job.company, job.title, job.location, job.description, job.employment_type)).lower()


def _evidence(rule_map: dict[str, object], matches: tuple[str, ...]) -> tuple[str, ...]:
    return tuple(f"{phrase}: {rule_map[phrase]}" for phrase in matches)


def required_experience_years(text: str) -> int | None:
    normalized = text.lower().replace("–", "-").replace("—", "-")
    patterns = (
        r"(?:minimum|min\.?|at least|over|more than)\s+(\d{1,2})\+?\s+years?",
        r"(\d{1,2})\+\s+years?",
        r"(\d{1,2})\s*(?:-|to)\s*(\d{1,2})\s+years?",
        r"(\d{1,2})\s+years?\s+(?:minimum|required|of experience)",
    )
    values: list[int] = []
    for pattern in patterns:
        for match in re.finditer(pattern, normalized):
            values.append(int(match.group(1)))
    return max(values) if values else None


def career_level(job: Job, years: int | None = None) -> str:
    title = job.title.lower()
    text = _text(job)
    years = required_experience_years(text) if years is None else years
    if any(term in title for term in HARD_SENIOR_TITLE_TERMS):
        return "SENIOR"
    if years is not None and years >= 5:
        return "SENIOR"
    if any(term in title for term in ("assistant", "coordinator", "junior", "associate", "administrator", "officer", "paralegal", "caseworker")):
        return "ENTRY"
    if any(term in title for term in ("manager", "specialist", "generalist", "partner")):
        return "MID"
    return "UNKNOWN"


def _restricted_location_without_opening(job: Job, text: str, internationally_open: bool) -> str | None:
    location = job.location.lower().strip()
    if internationally_open:
        return None
    if contains_any(text, REGION_RESTRICTION_TERMS):
        return "Region-restricted remote role"
    restricted_locations = (
        "united states", "usa", "u.s.", "canada", "australia",
        "new zealand", "latin america", "latam", "south africa",
        "philippines", "colombia", "india only",
    )
    if any(term in location for term in restricted_locations):
        return "Location is restricted and international hiring is not stated"
    return None





def discovery_only_reason(job: Job) -> str | None:
    host = (urlparse(job.url).hostname or "").lower()
    source = job.source.strip().lower()
    company = job.company.strip().lower()
    for domain in DISCOVERY_ONLY_AUTOMATION_DOMAINS:
        normalized = domain.lower().lstrip(".")
        if host == normalized or host.endswith("." + normalized):
            return f"Discovery-only marketplace domain: {normalized}"
    if source in DISCOVERY_ONLY_SOURCES:
        return f"Discovery-only source: {job.source}"
    if company in DISCOVERY_ONLY_COMPANIES:
        return f"Discovery-only marketplace company: {job.company}"
    return None

def blocked_automation_domain(url: str) -> str | None:
    host = (urlparse(url).hostname or "").lower()
    for domain in BLOCKED_AUTOMATION_DOMAINS:
        normalized = domain.lower().lstrip(".")
        if host == normalized or host.endswith("." + normalized):
            return normalized
    return None

def assess_eligibility(job: Job) -> EligibilityDecision:
    text = _text(job)
    blocked_domain = blocked_automation_domain(job.url)
    discovery_only = discovery_only_reason(job)
    market = assess_market(job)
    ngo = assess_ngo(job)

    geography_hits = matched_terms(text, HARD_GEOGRAPHY_RULES)
    language_hits = matched_terms(text, LOCAL_LANGUAGE_RULES)
    negative_hits = matched_terms(text, NEGATIVE_SPONSORSHIP_RULES)
    positive_hits = matched_terms(text, POSITIVE_SPONSORSHIP_RULES)
    relocation_hits = matched_terms(text, RELOCATION_RULES)

    negative_score = sum(NEGATIVE_SPONSORSHIP_RULES[item] for item in negative_hits)
    positive_score = sum(POSITIVE_SPONSORSHIP_RULES[item] for item in positive_hits)
    sponsorship_score = max(-100, min(100, negative_score or positive_score))

    if sponsorship_score >= 35:
        sponsorship_label = "YES"
    elif sponsorship_score <= -40:
        sponsorship_label = "NO"
    elif sponsorship_score > 0:
        sponsorship_label = "POSSIBLE"
    else:
        sponsorship_label = "UNKNOWN"

    relocation_label = "YES" if relocation_hits else "UNKNOWN"
    explicit_international = contains_any(text, INTERNATIONAL_OPENNESS_TERMS)
    internationally_open = bool(
        market.global_remote or positive_hits or relocation_hits or explicit_international
    )
    international_hiring_label = "LIKELY" if internationally_open else "UNKNOWN"

    years = required_experience_years(text)
    level = career_level(job, years)
    restricted_location_reason = _restricted_location_without_opening(job, text, internationally_open)

    codes: list[str] = []
    evidence: list[str] = []
    if blocked_domain:
        codes.append("BLOCKED_AUTOMATION_SOURCE")
        evidence.append(f"Blocked source domain: {blocked_domain}")
    if discovery_only:
        codes.append("DISCOVERY_ONLY_SOURCE")
        evidence.append(discovery_only)
    if geography_hits:
        codes.append("GEOGRAPHY_RESTRICTED")
        evidence.extend(_evidence(HARD_GEOGRAPHY_RULES, geography_hits))
    if restricted_location_reason:
        codes.append("GEOGRAPHY_RESTRICTED")
        evidence.append(restricted_location_reason)
    if language_hits:
        codes.append("LOCAL_LANGUAGE_REQUIRED")
        evidence.extend(_evidence(LOCAL_LANGUAGE_RULES, language_hits))
    if negative_hits:
        codes.append("SPONSORSHIP_UNAVAILABLE")
        evidence.extend(_evidence(NEGATIVE_SPONSORSHIP_RULES, negative_hits))
    if positive_hits:
        codes.append("SPONSORSHIP_AVAILABLE")
        evidence.extend(_evidence(POSITIVE_SPONSORSHIP_RULES, positive_hits))
    if relocation_hits:
        codes.append("RELOCATION_AVAILABLE")
        evidence.extend(_evidence(RELOCATION_RULES, relocation_hits))
    if level == "SENIOR":
        codes.append("SENIORITY_TOO_HIGH")
        evidence.append(f"Career level: {level}")
    if years is not None:
        evidence.append(f"Minimum experience detected: {years} years")
        if years > MAX_AUTOMATION_REQUIRED_YEARS:
            codes.append("EXPERIENCE_TOO_HIGH")
    if level == "ENTRY":
        codes.append("ENTRY_LEVEL_MATCH")
    elif level == "MID":
        codes.append("MID_LEVEL_MATCH")
    if ngo.label == "NGO_PRIORITY":
        codes.append("NGO_PRIORITY")

    if blocked_domain:
        verdict = "BLOCK"
        primary_reason = f"Source disabled because it uses anti-bot verification: {blocked_domain}"
    elif discovery_only:
        verdict = "BLOCK"
        primary_reason = discovery_only
    elif geography_hits:
        verdict = "BLOCK"
        primary_reason = HARD_GEOGRAPHY_RULES[geography_hits[0]]
    elif restricted_location_reason:
        verdict = "BLOCK"
        primary_reason = restricted_location_reason
    elif language_hits:
        verdict = "BLOCK"
        primary_reason = LOCAL_LANGUAGE_RULES[language_hits[0]]
    elif BLOCK_SENIOR_TITLES and level == "SENIOR":
        verdict = "BLOCK"
        primary_reason = "Senior-level role is outside the current entry-to-mid strategy"
    elif years is not None and years > MAX_AUTOMATION_REQUIRED_YEARS:
        verdict = "BLOCK"
        primary_reason = f"Role requires at least {years} years of experience"
    elif not market.supported:
        verdict = "BLOCK"
        primary_reason = "Unsupported, regional-only, or unclear work location"
        codes.append("MARKET_UNSUPPORTED")
    elif sponsorship_label == "NO" and not market.global_remote:
        verdict = "BLOCK"
        primary_reason = "Employer sponsorship is unavailable"
    elif sponsorship_label == "NO" and market.global_remote:
        verdict = "APPLY"
        primary_reason = "Worldwide remote role does not require relocation sponsorship"
        codes.append("GLOBAL_REMOTE")
    elif sponsorship_label in {"YES", "POSSIBLE"} or relocation_label == "YES":
        verdict = "PRIORITY"
        primary_reason = "International hiring or relocation support detected"
    elif market.global_remote or explicit_international:
        verdict = "APPLY"
        primary_reason = "Worldwide or international eligibility detected"
        codes.append("GLOBAL_REMOTE")
    elif STRICT_ELIGIBILITY_MODE:
        verdict = "REVIEW"
        primary_reason = "International eligibility is not explicit"
        codes.append("ELIGIBILITY_UNCONFIRMED")
    else:
        verdict = "REVIEW"
        primary_reason = "Work eligibility is not explicit"
        codes.append("ELIGIBILITY_UNCONFIRMED")

    evidence_count = len(evidence)
    confidence = min(98, 40 + evidence_count * 10)
    if verdict == "REVIEW":
        confidence = min(confidence, 45)

    return EligibilityDecision(
        verdict=verdict,
        primary_reason=primary_reason,
        reason_codes=tuple(dict.fromkeys(codes)),
        evidence=tuple(evidence),
        confidence=confidence,
        sponsorship_label=sponsorship_label,
        sponsorship_score=sponsorship_score,
        relocation_label=relocation_label,
        international_hiring_label=international_hiring_label,
        ngo_label=ngo.label,
        ngo_bonus=ngo.score,
        market_supported=market.supported,
        market_score=market.market_score,
        language_penalty=market.language_penalty,
        global_remote=market.global_remote,
        career_level=level,
        required_years=years,
    )


def production_block_reason(job: Job) -> str | None:
    """Hard gate used before persistence and automation without changing research verdicts."""
    decision = assess_eligibility(job)
    if decision.blocked:
        return decision.primary_reason
    if decision.global_remote:
        return None
    if decision.market_supported and decision.market_score >= 80:
        if decision.sponsorship_label in {"YES", "POSSIBLE"} or decision.relocation_label == "YES" or decision.international_hiring_label == "LIKELY":
            return None
        return "Target-country role lacks explicit sponsorship, relocation, or international eligibility"
    return "Role is not explicitly worldwide remote or an eligible target-country vacancy"


def is_production_eligible(job: Job) -> bool:
    return production_block_reason(job) is None

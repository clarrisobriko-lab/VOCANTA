from dataclasses import dataclass
from typing import Any
from urllib.parse import urlparse

try:
    from playwright.sync_api import Page
except ModuleNotFoundError:
    Page = Any


@dataclass(frozen=True, slots=True)
class WorkdayGate:
    blocked: bool
    reason: str = ""


@dataclass(frozen=True, slots=True)
class WorkdayState:
    stage: str
    confirmation: bool = False
    reason: str = ""


def is_workday_url(url: str) -> bool:
    host = (urlparse(url).hostname or "").lower()
    return host.endswith("workday.com") or host.endswith("myworkdayjobs.com")


def _body_text(page: Page) -> str:
    try:
        return " ".join(page.locator("body").inner_text().lower().split())
    except Exception:
        return ""


def detect_workday_gate(page: Page) -> WorkdayGate:
    """Detect Workday states that must not be treated as an application form."""
    url = str(getattr(page, "url", "") or "")
    if not is_workday_url(url):
        return WorkdayGate(False)

    text = _body_text(page)
    account_markers = (
        "sign in to your account",
        "sign in with your account",
        "create account",
        "create an account",
        "already have an account",
        "candidate home",
    )
    marker = next((item for item in account_markers if item in text), "")
    if marker:
        return WorkdayGate(True, f"Workday account gate detected: {marker}")

    path = urlparse(url).path.lower()
    if any(token in path for token in ("/login", "/signin", "/candidatehome")):
        return WorkdayGate(True, f"Workday account route detected: {path}")

    return WorkdayGate(False)


def detect_workday_state(page: Page) -> WorkdayState:
    """Classify Workday application progress without guessing submission success."""
    url = str(getattr(page, "url", "") or "")
    if not is_workday_url(url):
        return WorkdayState("NOT_WORKDAY")

    gate = detect_workday_gate(page)
    if gate.blocked:
        return WorkdayState("ACCOUNT_GATE", reason=gate.reason)

    text = _body_text(page)
    confirmations = (
        "application submitted",
        "thank you for applying",
        "thanks for applying",
        "we have received your application",
        "application has been received",
        "your application was submitted",
        "your application has been submitted",
    )
    marker = next((item for item in confirmations if item in text), "")
    if marker:
        return WorkdayState("CONFIRMED", confirmation=True, reason=marker)

    review_markers = (
        "review your application",
        "review application",
        "application review",
    )
    if any(item in text for item in review_markers):
        return WorkdayState("REVIEW")

    application_markers = (
        "my information",
        "my experience",
        "application questions",
        "voluntary disclosures",
        "resume/cv",
        "resume / cv",
    )
    if any(item in text for item in application_markers):
        return WorkdayState("APPLICATION")

    return WorkdayState("UNKNOWN")

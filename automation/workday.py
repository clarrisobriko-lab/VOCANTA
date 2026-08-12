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


def is_workday_url(url: str) -> bool:
    host = (urlparse(url).hostname or "").lower()
    return host.endswith("workday.com") or host.endswith("myworkdayjobs.com")


def detect_workday_gate(page: Page) -> WorkdayGate:
    """Detect Workday states that must not be treated as an application form.

    Workday tenants can require an account/sign-in step before exposing the
    actual application. VOCANTA must stop safely rather than filling login
    credentials, creating an account, or mistaking those controls for a job
    application.
    """
    url = str(getattr(page, "url", "") or "")
    if not is_workday_url(url):
        return WorkdayGate(False)

    try:
        text = " ".join(page.locator("body").inner_text().lower().split())
    except Exception:
        text = ""

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

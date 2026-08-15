from __future__ import annotations

from dataclasses import dataclass
from typing import Any


SUCCESS_PHRASES = (
    "application submitted", "application successfully submitted", "application received",
    "thank you for applying", "thanks for applying", "we have received your application",
    "your application has been submitted", "application complete",
)
ACCOUNT_PHRASES = (
    "create account", "sign in to apply", "log in to apply", "login to apply",
    "create a password", "verify your email", "email verification",
)
CHALLENGE_PHRASES = (
    "captcha", "verify you are human", "security check", "two-factor",
    "verification code", "one-time code", "one time code",
)


@dataclass(frozen=True, slots=True)
class BrowserState:
    submitted: bool
    account_required: bool
    human_challenge: bool
    reason: str


def classify_page_text(text: str) -> BrowserState:
    normalized = " ".join((text or "").lower().split())
    if any(phrase in normalized for phrase in SUCCESS_PHRASES):
        return BrowserState(True, False, False, "submission confirmation detected")
    if any(phrase in normalized for phrase in CHALLENGE_PHRASES):
        return BrowserState(False, False, True, "human verification required")
    if any(phrase in normalized for phrase in ACCOUNT_PHRASES):
        return BrowserState(False, True, False, "account or email verification required")
    return BrowserState(False, False, False, "no terminal browser state detected")


def inspect_browser_state(page: Any) -> BrowserState:
    texts: list[str] = []
    try:
        texts.append(page.locator("body").inner_text(timeout=3000))
    except Exception:
        pass
    for frame in getattr(page, "frames", ()):
        try:
            texts.append(frame.locator("body").inner_text(timeout=1500))
        except Exception:
            continue
    return classify_page_text("\n".join(texts))


def wait_for_submission_confirmation(page: Any, timeout_ms: int = 10000) -> BrowserState:
    elapsed = 0
    while elapsed <= timeout_ms:
        state = inspect_browser_state(page)
        if state.submitted or state.account_required or state.human_challenge:
            return state
        try:
            page.wait_for_timeout(500)
        except Exception:
            break
        elapsed += 500
    return inspect_browser_state(page)

from collections.abc import Callable
import logging
from dataclasses import dataclass, replace
from pathlib import Path
from urllib.parse import urlparse
from typing import Any

try:
    from playwright.sync_api import (
        BrowserContext,
        Page,
        TimeoutError as PlaywrightTimeoutError,
        sync_playwright,
    )
except ModuleNotFoundError:  # Allows policy and unit tests before installation.
    BrowserContext = Page = Any
    PlaywrightTimeoutError = TimeoutError
    sync_playwright = None

from automation.ats import ATSAdapter, adapter_for_url
from automation.forms import (
    FillResult,
    click_next_step,
    click_safe_submit,
    fill_application_form,
)
from automation.profile import ApplicantProfile
from automation.diagnostics import ApplicationDiagnostics
from automation.page_registry import PageRegistry
from config.settings import (
    AUTOMATION_AUTO_SUBMIT_STANDARD_FORMS,
    AUTOMATION_HEADLESS,
    AUTOMATION_HUMAN_POLL_SECONDS,
    AUTOMATION_HUMAN_WAIT_SECONDS,
    AUTOMATION_SCREENSHOT_DIR,
    BROWSER_PROFILE_DIR,
    BLOCKED_AUTOMATION_DOMAINS,
)


StateCallback = Callable[[str, dict[str, str]], None]
HumanActionCallback = Callable[[str, str, str, str], None]
logger = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class AutomationResult:
    status: str
    message: str
    screenshot: str
    filled_fields: int
    confirmation_url: str = ""
    confirmation_text: str = ""
    submit_control: str = ""
    fields_detected: int = 0
    required_fields: int = 0
    required_manual: int = 0
    optional_skipped: int = 0
    cv_uploaded: bool = False
    cover_letter_uploaded: bool = False
    report_path: str = ""


def _blocked_domain(url: str) -> str | None:
    host = (urlparse(url).hostname or "").lower()
    for domain in BLOCKED_AUTOMATION_DOMAINS:
        normalized = domain.lower().lstrip(".")
        if host == normalized or host.endswith("." + normalized):
            return normalized
    return None


def ats_name(url: str) -> str:
    return adapter_for_url(url).name


def _open_application_form(page: Page, registry: PageRegistry) -> Page:
    page.wait_for_load_state("domcontentloaded")
    selectors = (
        'a:has-text("Apply for this job")',
        'button:has-text("Apply for this job")',
        'a:has-text("Apply now")',
        'button:has-text("Apply now")',
        'a:has-text("Apply")',
        'button:has-text("Apply")',
    )
    for selector in selectors:
        locator = page.locator(selector)
        for index in range(locator.count()):
            item = locator.nth(index)
            try:
                if item.is_visible() and item.is_enabled():
                    before = registry.snapshot()
                    item.click()
                    try:
                        page.wait_for_load_state(
                            "domcontentloaded",
                            timeout=15_000,
                        )
                    except PlaywrightTimeoutError:
                        pass
                    return registry.after_action(page, before)
            except Exception:
                continue
    return registry.recover(page) or page


@dataclass(frozen=True, slots=True)
class VerificationDetection:
    blocked: bool
    reasons: tuple[str, ...]


def _visible_count(page: Page, selector: str) -> int:
    try:
        locator = page.locator(selector)
        visible = 0
        for index in range(locator.count()):
            try:
                if locator.nth(index).is_visible():
                    visible += 1
            except Exception:
                continue
        return visible
    except Exception:
        return 0


def _visible_body_text(page: Page) -> str:
    try:
        return " ".join(page.locator("body").inner_text().lower().split())
    except Exception:
        return ""


def _has_standard_application_form(page: Page) -> bool:
    selectors = (
        'input[type="email"]',
        'input[name*="email" i]',
        'input[autocomplete="email"]',
        'input[type="file"]',
        'form input:not([type="hidden"])',
    )
    return any(_visible_count(page, selector) > 0 for selector in selectors)


def _detect_human_verification(page: Page) -> VerificationDetection:
    """Detect only an active, visible verification challenge.

    ATS pages frequently preload reCAPTCHA or hCaptcha scripts even when no
    challenge is shown. Raw HTML keyword matching therefore creates false
    positives. This detector requires a visible challenge widget, a dedicated
    challenge URL, or challenge text on a page that does not expose a normal
    application form.
    """
    reasons: list[str] = []
    url = str(getattr(page, "url", "") or "").lower()
    host = (urlparse(url).hostname or "").lower()

    widget_selectors = {
        "visible reCAPTCHA iframe": (
            'iframe[src*="recaptcha" i], iframe[title*="recaptcha" i]'
        ),
        "visible hCaptcha iframe": (
            'iframe[src*="hcaptcha" i], iframe[title*="hcaptcha" i]'
        ),
        "visible Cloudflare Turnstile widget": (
            'iframe[src*="challenges.cloudflare.com" i], .cf-turnstile, '
            '[data-sitekey][class*="turnstile" i]'
        ),
        "visible CAPTCHA container": (
            '.g-recaptcha, .h-captcha, [class*="captcha" i]:not(script)'
        ),
    }
    for reason, selector in widget_selectors.items():
        count = _visible_count(page, selector)
        if count:
            reasons.append(f"{reason} ({count})")

    challenge_paths = (
        "/cdn-cgi/challenge-platform/",
        "/challenge/",
        "/captcha/",
    )
    if any(path in url for path in challenge_paths):
        reasons.append(f"challenge URL detected: {url}")

    body_text = _visible_body_text(page)
    challenge_phrases = (
        "verify you are human",
        "verifying you are human",
        "performing security verification",
        "checking your browser before accessing",
        "complete the security check",
        "are you a human",
    )
    form_visible = _has_standard_application_form(page)
    matched_text = next(
        (phrase for phrase in challenge_phrases if phrase in body_text),
        "",
    )
    if matched_text and not form_visible:
        reasons.append(f'visible challenge text: "{matched_text}"')

    # Greenhouse embeds CAPTCHA libraries in ordinary forms. Those scripts are
    # not evidence of a challenge. A visible standard form wins unless an
    # actual widget or challenge route was detected above.
    if form_visible and "greenhouse" in host:
        reasons = [
            reason for reason in reasons
            if not reason.startswith("visible challenge text")
        ]

    detection = VerificationDetection(bool(reasons), tuple(reasons))
    logger.info(
        "Human verification audit | blocked=%s | url=%s | "
        "standard_form=%s | reasons=%s",
        detection.blocked,
        url,
        form_visible,
        "; ".join(detection.reasons) or "none",
    )
    return detection


def _has_captcha(page: Page) -> bool:
    return _detect_human_verification(page).blocked


def _confirmation(page: Page, adapter: ATSAdapter) -> str:
    content = page.content().lower()
    return next(
        (phrase for phrase in adapter.confirmation_phrases if phrase in content),
        "",
    )


def _wait_after_action(page: Page) -> None:
    try:
        page.wait_for_load_state("networkidle", timeout=15_000)
    except PlaywrightTimeoutError:
        page.wait_for_timeout(2_000)


def _screenshot(page: Page, path: Path) -> None:
    try:
        if not page.is_closed():
            page.screenshot(path=str(path), full_page=True)
    except Exception:
        pass


def _emit(
    callback: StateCallback | None,
    status: str,
    *,
    screenshot: str = "",
    confirmation_url: str = "",
    confirmation_text: str = "",
    last_error: str = "",
    active_url: str = "",
) -> None:
    if callback is not None:
        callback(
            status,
            {
                "screenshot_path": screenshot,
                "confirmation_url": confirmation_url,
                "confirmation_text": confirmation_text,
                "last_error": last_error,
                "active_url": active_url,
            },
        )


def _manual_checkpoint(
    page: Page,
    screenshot: Path,
    prompt: str,
    filled_fields: int,
    fallback_status: str,
    fallback_message: str,
    adapter: ATSAdapter,
    state_callback: StateCallback | None,
    registry: PageRegistry,
    human_action_callback: HumanActionCallback | None = None,
) -> AutomationResult:
    page = registry.recover(page) or page
    _screenshot(page, screenshot)
    active_url = str(getattr(page, "url", "") or "")
    _emit(
        state_callback,
        fallback_status,
        screenshot=str(screenshot),
        active_url=active_url,
    )
    if human_action_callback is not None:
        try:
            human_action_callback(
                fallback_status,
                fallback_message,
                str(screenshot),
                active_url,
            )
        except Exception as exc:
            logger.exception(
                "Immediate human-action notification callback failed | status=%s | url=%s | error=%s: %s",
                fallback_status,
                active_url,
                type(exc).__name__,
                exc,
            )

    print()
    print(prompt)
    print(
        f"VOCANTA will watch the browser for up to "
        f"{AUTOMATION_HUMAN_WAIT_SECONDS} seconds, then continue automatically."
    )

    elapsed = 0
    while elapsed < AUTOMATION_HUMAN_WAIT_SECONDS:
        try:
            recovered = registry.recover(page)
            if recovered is None:
                return AutomationResult(
                    status=fallback_status,
                    message=(
                        fallback_message
                        + " The browser page was closed, so VOCANTA continued."
                    ),
                    screenshot=str(screenshot),
                    filled_fields=filled_fields,
                )
            page = recovered

            confirmation = _confirmation(page, adapter)
            if confirmation:
                _screenshot(page, screenshot)
                confirmation_url = page.url
                _emit(
                    state_callback,
                    "CONFIRMED",
                    screenshot=str(screenshot),
                    confirmation_url=confirmation_url,
                    confirmation_text=confirmation,
                    active_url=confirmation_url,
                )
                return AutomationResult(
                    status="AUTO_SUBMITTED",
                    message="Application submission confirmed after human assistance.",
                    screenshot=str(screenshot),
                    filled_fields=filled_fields,
                    confirmation_url=confirmation_url,
                    confirmation_text=confirmation,
                )

            page.wait_for_timeout(AUTOMATION_HUMAN_POLL_SECONDS * 1000)
            elapsed += AUTOMATION_HUMAN_POLL_SECONDS
        except Exception:
            recovered = registry.recover(page)
            if recovered is not None and recovered is not page:
                page = recovered
                continue
            return AutomationResult(
                status=fallback_status,
                message=(
                    fallback_message
                    + " The browser became unavailable, so VOCANTA continued."
                ),
                screenshot=str(screenshot),
                filled_fields=filled_fields,
            )

    _screenshot(page, screenshot)
    return AutomationResult(
        status=fallback_status,
        message=(
            fallback_message
            + f" Human action was not completed within "
            f"{AUTOMATION_HUMAN_WAIT_SECONDS} seconds."
        ),
        screenshot=str(screenshot),
        filled_fields=filled_fields,
    )


def _write_diagnostics(url: str, job_id: int, result: AutomationResult) -> AutomationResult:
    diagnostics = ApplicationDiagnostics(
        application_id=f"{ats_name(url)}-{job_id}",
        ats=ats_name(url),
        url=url,
        fields_detected=result.fields_detected,
        required_fields=result.required_fields,
        filled_automatically=result.filled_fields,
        required_manual=result.required_manual,
        optional_skipped=result.optional_skipped,
        cv_uploaded=result.cv_uploaded,
        cover_letter_uploaded=result.cover_letter_uploaded,
        submitted=result.status in {"AUTO_SUBMITTED", "SUBMISSION_UNVERIFIED"},
        submission_verified=result.status == "AUTO_SUBMITTED",
        submission_evidence=result.confirmation_text or result.confirmation_url,
        blocked_reason=result.message if result.status in {"MANUAL_REQUIRED", "HUMAN_VERIFICATION", "FAILED", "UNKNOWN"} else "",
    )
    path = diagnostics.save()
    logger.info("Application diagnostics written | job_id=%s | path=%s", job_id, path)
    return replace(result, report_path=str(path))


class BrowserApplicationEngine:
    def __init__(
        self,
        profile: ApplicantProfile,
        state_callback: StateCallback | None = None,
        human_action_callback: HumanActionCallback | None = None,
    ) -> None:
        self.profile = profile
        self.state_callback = state_callback
        self.human_action_callback = human_action_callback

    def apply(self, url: str, job_id: int) -> AutomationResult:
        blocked_domain = _blocked_domain(url)
        if blocked_domain:
            return _write_diagnostics(url, job_id, AutomationResult(
                status="SKIPPED_SOURCE",
                message=f"Browser launch blocked for {blocked_domain}. Cloudflare-protected sources are disabled.",
                screenshot="", filled_fields=0,
            ))
        if sync_playwright is None:
            return _write_diagnostics(url, job_id, AutomationResult(
                status="FAILED", message="Playwright is not installed. Run install.bat first.",
                screenshot="", filled_fields=0,
            ))
        first = self._apply_once(url, job_id, 0)
        recoverable = first.status == "FAILED" and any(marker in first.message.lower() for marker in (
            "targetclosederror", "target page, context or browser has been closed",
            "browser has been closed", "page was closed",
        ))
        result = self._apply_once(url, job_id, 1) if recoverable else first
        return _write_diagnostics(url, job_id, result)

    def _apply_once(self, url: str, job_id: int, attempt: int) -> AutomationResult:
        AUTOMATION_SCREENSHOT_DIR.mkdir(parents=True, exist_ok=True)
        BROWSER_PROFILE_DIR.mkdir(parents=True, exist_ok=True)
        screenshot = (
            AUTOMATION_SCREENSHOT_DIR
            / f"job_{job_id}_attempt_{attempt + 1}.png"
        )
        submit_started = False

        with sync_playwright() as playwright:
            context: BrowserContext = playwright.chromium.launch_persistent_context(
                user_data_dir=str(BROWSER_PROFILE_DIR),
                headless=AUTOMATION_HEADLESS,
                viewport={"width": 1440, "height": 1000},
                accept_downloads=True,
            )
            page = context.pages[0] if context.pages else context.new_page()
            registry = PageRegistry(context)

            try:
                page.goto(url, wait_until="domcontentloaded", timeout=60_000)
                redirected_domain = _blocked_domain(page.url or url)
                if redirected_domain:
                    return AutomationResult(
                        status="SKIPPED_SOURCE",
                        message=(
                            f"Redirected to disabled source {redirected_domain}. "
                            "The browser was closed without waiting for verification."
                        ),
                        screenshot="",
                        filled_fields=0,
                    )
                page = _open_application_form(page, registry)
                redirected_domain = _blocked_domain(page.url or url)
                if redirected_domain:
                    return AutomationResult(
                        status="SKIPPED_SOURCE",
                        message=(
                            f"Application redirected to disabled source {redirected_domain}. "
                            "The browser was closed without waiting for verification."
                        ),
                        screenshot="",
                        filled_fields=0,
                    )
                adapter = adapter_for_url(page.url or url)

                verification = _detect_human_verification(page)
                if verification.blocked:
                    reason_text = "; ".join(verification.reasons)
                    _emit(
                        self.state_callback,
                        "BLOCKED",
                        last_error=reason_text,
                        active_url=str(page.url or url),
                    )
                    return AutomationResult(
                        status="SKIPPED_SOURCE",
                        message=(
                            "Security verification detected before form completion: "
                            f"{reason_text}. The page was closed immediately."
                        ),
                        screenshot="",
                        filled_fields=0,
                    )

                total_filled = 0
                fill_result: FillResult | None = None
                for _ in range(4):
                    fill_result = fill_application_form(
                        page,
                        self.profile,
                        adapter.final_submit_texts,
                    )
                    total_filled += fill_result.filled
                    if fill_result.restricted_questions:
                        questions = "; ".join(fill_result.restricted_questions[:6])
                        return _manual_checkpoint(
                            page, screenshot,
                            "Employer requires your own words for: " + questions,
                            total_filled, "MANUAL_REQUIRED",
                            "AI-restricted questions require your personal response. The application was not submitted.",
                            adapter, self.state_callback, registry, self.human_action_callback,
                        )
                    _emit(
                        self.state_callback,
                        "FORM_FILLED",
                        active_url=str(page.url or ""),
                    )

                    if fill_result.required_unanswered:
                        fields = "; ".join(fill_result.required_unanswered[:8])
                        return _manual_checkpoint(
                            page,
                            screenshot,
                            (
                                "Employer-specific required questions need your answer:\n"
                                f"{fields}"
                            ),
                            total_filled,
                            "READY_TO_REVIEW",
                            (
                                "Required questions remain or submission confirmation "
                                "was not detected."
                            ),
                            adapter,
                            self.state_callback,
                            registry,
                            self.human_action_callback,
                        )

                    if fill_result.safe_submit_found:
                        break

                    if fill_result.next_step_found:
                        before = registry.snapshot()
                        if not click_next_step(page):
                            break
                        page = registry.after_action(page, before)
                        _wait_after_action(page)
                        verification = _detect_human_verification(page)
                        if verification.blocked:
                            reason_text = "; ".join(verification.reasons)
                            return _manual_checkpoint(
                                page,
                                screenshot,
                                (
                                    "Human verification appeared on the next step.\n"
                                    f"Detection reason: {reason_text}"
                                ),
                                total_filled,
                                "HUMAN_VERIFICATION",
                                (
                                    "Human verification remains unresolved. "
                                    "The application was not submitted."
                                ),
                                adapter,
                                self.state_callback,
                                registry,
                                self.human_action_callback,
                            )
                        continue
                    break

                _screenshot(page, screenshot)

                if not fill_result or not fill_result.safe_submit_found:
                    return _manual_checkpoint(
                        page,
                        screenshot,
                        (
                            "VOCANTA filled the available fields but could not safely "
                            "identify the final submission control."
                        ),
                        total_filled,
                        "READY_TO_REVIEW",
                        (
                            "Application is prepared for review. "
                            "A verified final submit control was not detected."
                        ),
                        adapter,
                        self.state_callback,
                        registry,
                        self.human_action_callback,
                    )

                if not adapter.auto_submit_allowed:
                    return _manual_checkpoint(
                        page,
                        screenshot,
                        (
                            f"{adapter.name} is review-only in this release. "
                            "The form is ready for your final review."
                        ),
                        total_filled,
                        "READY_TO_REVIEW",
                        "Application remains ready for manual submission.",
                        adapter,
                        self.state_callback,
                        registry,
                        self.human_action_callback,
                    )

                if not AUTOMATION_AUTO_SUBMIT_STANDARD_FORMS:
                    return _manual_checkpoint(
                        page,
                        screenshot,
                        "The application is ready for your final review.",
                        total_filled,
                        "READY_TO_REVIEW",
                        "Application remains ready for manual submission.",
                        adapter,
                        self.state_callback,
                        registry,
                        self.human_action_callback,
                    )

                _emit(
                    self.state_callback,
                    "SUBMITTING",
                    screenshot=str(screenshot),
                    active_url=str(page.url or ""),
                )
                submit_started = True
                before = registry.snapshot()
                if not click_safe_submit(page, adapter.final_submit_texts):
                    _emit(
                        self.state_callback,
                        "UNKNOWN",
                        screenshot=str(screenshot),
                        last_error="Final submit control changed before click.",
                        active_url=str(page.url or ""),
                    )
                    return AutomationResult(
                        status="UNKNOWN",
                        message=(
                            "The final control changed after submission was armed. "
                            "Review before any retry."
                        ),
                        screenshot=str(screenshot),
                        filled_fields=total_filled,
                    )

                page = registry.after_action(page, before)
                _emit(
                    self.state_callback,
                    "SUBMITTED",
                    screenshot=str(screenshot),
                    active_url=str(page.url or ""),
                )
                _wait_after_action(page)
                _screenshot(page, screenshot)

                verification = _detect_human_verification(page)
                if verification.blocked:
                    reason_text = "; ".join(verification.reasons)
                    return _manual_checkpoint(
                        page,
                        screenshot,
                        (
                            "Human verification appeared during submission.\n"
                            f"Detection reason: {reason_text}"
                        ),
                        total_filled,
                        "UNKNOWN",
                        (
                            "Human verification remains unresolved. "
                            "Submission was not confirmed."
                        ),
                        adapter,
                        self.state_callback,
                        registry,
                        self.human_action_callback,
                    )

                confirmation = _confirmation(page, adapter)
                if confirmation:
                    confirmation_url = page.url
                    _emit(
                        self.state_callback,
                        "CONFIRMED",
                        screenshot=str(screenshot),
                        confirmation_url=confirmation_url,
                        confirmation_text=confirmation,
                        active_url=confirmation_url,
                    )
                    return AutomationResult(
                        status="AUTO_SUBMITTED",
                        message=f"Application submitted through {adapter.name}.",
                        screenshot=str(screenshot),
                        filled_fields=total_filled,
                        confirmation_url=confirmation_url,
                        confirmation_text=confirmation,
                        submit_control=adapter.final_submit_texts[0],
                        fields_detected=fill_result.fields_detected,
                        required_fields=fill_result.required_fields,
                        required_manual=0,
                        optional_skipped=fill_result.optional_skipped,
                        cv_uploaded=fill_result.cv_uploaded,
                        cover_letter_uploaded=fill_result.cover_letter_uploaded,
                    )

                return _manual_checkpoint(
                    page,
                    screenshot,
                    (
                        "VOCANTA clicked the final control, but the employer did not "
                        "show a recognised confirmation. Verify the browser."
                    ),
                    total_filled,
                    "UNKNOWN",
                    (
                        "Submission confirmation was not detected. "
                        "Review before any retry to avoid a duplicate application."
                    ),
                    adapter,
                    self.state_callback,
                    registry,
                    self.human_action_callback,
                )
            except PlaywrightTimeoutError:
                status = "UNKNOWN" if submit_started else "FAILED"
                message = (
                    "The page timed out after submission began. Do not retry automatically."
                    if submit_started
                    else "The application page timed out."
                )
                _emit(
                    self.state_callback,
                    status,
                    screenshot=str(screenshot),
                    last_error=message,
                    active_url=str(getattr(page, "url", "") or ""),
                )
                return AutomationResult(
                    status=status,
                    message=message,
                    screenshot=str(screenshot),
                    filled_fields=0,
                )
            except Exception as exc:
                status = "UNKNOWN" if submit_started else "FAILED"
                message = f"{type(exc).__name__}: {exc}"
                _emit(
                    self.state_callback,
                    status,
                    screenshot=str(screenshot),
                    last_error=message,
                    active_url=str(getattr(page, "url", "") or ""),
                )
                return AutomationResult(
                    status=status,
                    message=message,
                    screenshot=str(screenshot),
                    filled_fields=0,
                )
            finally:
                context.close()

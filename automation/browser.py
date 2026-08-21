from collections.abc import Callable
import logging
from dataclasses import dataclass, replace
from pathlib import Path
from urllib.parse import urlparse
from typing import Any

try:
    from playwright.sync_api import BrowserContext, Page, TimeoutError as PlaywrightTimeoutError, sync_playwright
except ModuleNotFoundError:
    BrowserContext = Page = Any
    PlaywrightTimeoutError = TimeoutError
    sync_playwright = None

from automation.ats import ATSAdapter, adapter_for_url
from automation.forms import FillResult, click_next_step, click_safe_submit, fill_application_form
from automation.profile import ApplicantProfile
from automation.diagnostics import ApplicationDiagnostics
from automation.page_registry import PageRegistry
from automation.workday import detect_workday_gate
from config.settings import AUTOMATION_AUTO_SUBMIT_STANDARD_FORMS, AUTOMATION_HEADLESS, AUTOMATION_HUMAN_POLL_SECONDS, AUTOMATION_HUMAN_WAIT_SECONDS, AUTOMATION_SCREENSHOT_DIR, BROWSER_PROFILE_DIR, BLOCKED_AUTOMATION_DOMAINS

StateCallback = Callable[[str, dict[str, str]], None]
HumanActionCallback = Callable[[str, str, str, str], None]
logger = logging.getLogger(__name__)

@dataclass(frozen=True, slots=True)
class AutomationResult:
    status: str; message: str; screenshot: str; filled_fields: int; confirmation_url: str = ""; confirmation_text: str = ""; submit_control: str = ""; fields_detected: int = 0; required_fields: int = 0; required_manual: int = 0; optional_skipped: int = 0; cv_uploaded: bool = False; cover_letter_uploaded: bool = False; report_path: str = ""

def _blocked_domain(url: str) -> str | None:
    host=(urlparse(url).hostname or "").lower()
    for domain in BLOCKED_AUTOMATION_DOMAINS:
        normalized=domain.lower().lstrip(".")
        if host==normalized or host.endswith("."+normalized): return normalized
    return None

def ats_name(url:str)->str: return adapter_for_url(url).name

def _open_application_form(page:Page,registry:PageRegistry)->Page:
    page.wait_for_load_state("domcontentloaded")
    selectors=('a:has-text("Apply for this job")','button:has-text("Apply for this job")','a:has-text("Apply now")','button:has-text("Apply now")','a:has-text("Apply")','button:has-text("Apply")')
    for selector in selectors:
        locator=page.locator(selector)
        for index in range(locator.count()):
            item=locator.nth(index)
            try:
                if item.is_visible() and item.is_enabled():
                    before=registry.snapshot(); item.click()
                    try: page.wait_for_load_state("domcontentloaded",timeout=15_000)
                    except PlaywrightTimeoutError: pass
                    return registry.after_action(page,before)
            except Exception: continue
    return registry.recover(page) or page

@dataclass(frozen=True,slots=True)
class VerificationDetection:
    blocked: bool; reasons: tuple[str,...]

def _visible_count(page:Page,selector:str)->int:
    try:
        locator=page.locator(selector); visible=0
        for index in range(locator.count()):
            try:
                if locator.nth(index).is_visible(): visible += 1
            except Exception: continue
        return visible
    except Exception: return 0

def _visible_body_text(page:Page)->str:
    try: return " ".join(page.locator("body").inner_text().lower().split())
    except Exception: return ""

def _has_standard_application_form(page:Page)->bool:
    selectors=('input[type="email"]','input[name*="email" i]','input[autocomplete="email"]','input[type="file"]','form input:not([type="hidden"])')
    return any(_visible_count(page,s)>0 for s in selectors)

def _detect_human_verification(page:Page)->VerificationDetection:
    reasons=[]; url=str(getattr(page,"url","") or "").lower(); host=(urlparse(url).hostname or "").lower()
    widgets={"visible reCAPTCHA iframe":'iframe[src*="recaptcha" i], iframe[title*="recaptcha" i]',"visible hCaptcha iframe":'iframe[src*="hcaptcha" i], iframe[title*="hcaptcha" i]',"visible Cloudflare Turnstile widget":'iframe[src*="challenges.cloudflare.com" i], .cf-turnstile, [data-sitekey][class*="turnstile" i]',"visible CAPTCHA container":'.g-recaptcha, .h-captcha, [class*="captcha" i]:not(script)'}
    for reason,selector in widgets.items():
        count=_visible_count(page,selector)
        if count: reasons.append(f"{reason} ({count})")
    if any(path in url for path in ("/cdn-cgi/challenge-platform/","/challenge/","/captcha/")): reasons.append(f"challenge URL detected: {url}")
    body=_visible_body_text(page); matched=next((p for p in ("verify you are human","verifying you are human","performing security verification","checking your browser before accessing","complete the security check","are you a human") if p in body),""); form_visible=_has_standard_application_form(page)
    if matched and not form_visible: reasons.append(f'visible challenge text: "{matched}"')
    if form_visible and "greenhouse" in host: reasons=[r for r in reasons if not r.startswith("visible challenge text")]
    return VerificationDetection(bool(reasons),tuple(reasons))

def _has_captcha(page:Page)->bool: return _detect_human_verification(page).blocked

def _confirmation(page:Page,adapter:ATSAdapter)->str:
    content=page.content().lower(); return next((p for p in adapter.confirmation_phrases if p in content),"")

def _wait_after_action(page:Page)->None:
    try: page.wait_for_load_state("networkidle",timeout=15_000)
    except PlaywrightTimeoutError: page.wait_for_timeout(2_000)

def _screenshot(page:Page,path:Path)->None:
    try:
        if not page.is_closed(): page.screenshot(path=str(path),full_page=True)
    except Exception: pass

def _emit(callback,status,**kwargs):
    if callback is not None: callback(status,{"screenshot_path":kwargs.get("screenshot",""),"confirmation_url":kwargs.get("confirmation_url",""),"confirmation_text":kwargs.get("confirmation_text",""),"last_error":kwargs.get("last_error",""),"active_url":kwargs.get("active_url","")})

def _manual_checkpoint(page,screenshot,prompt,filled_fields,fallback_status,fallback_message,adapter,state_callback,registry,human_action_callback=None):
    page=registry.recover(page) or page; _screenshot(page,screenshot); active_url=str(getattr(page,"url","") or ""); _emit(state_callback,fallback_status,screenshot=str(screenshot),active_url=active_url)
    if human_action_callback:
        try: human_action_callback(fallback_status,fallback_message,str(screenshot),active_url)
        except Exception: pass
    elapsed=0
    while elapsed < AUTOMATION_HUMAN_WAIT_SECONDS:
        try:
            recovered=registry.recover(page)
            if recovered is None: return AutomationResult(fallback_status,fallback_message,str(screenshot),filled_fields)
            page=recovered; confirmation=_confirmation(page,adapter)
            if confirmation: return AutomationResult("AUTO_SUBMITTED","Application submission confirmed after human assistance.",str(screenshot),filled_fields,page.url,confirmation)
            page.wait_for_timeout(AUTOMATION_HUMAN_POLL_SECONDS*1000); elapsed += AUTOMATION_HUMAN_POLL_SECONDS
        except Exception: return AutomationResult(fallback_status,fallback_message,str(screenshot),filled_fields)
    return AutomationResult(fallback_status,fallback_message,str(screenshot),filled_fields)

def _write_diagnostics(url,job_id,result):
    diagnostics=ApplicationDiagnostics(application_id=f"{ats_name(url)}-{job_id}",ats=ats_name(url),url=url,fields_detected=result.fields_detected,required_fields=result.required_fields,filled_automatically=result.filled_fields,required_manual=result.required_manual,optional_skipped=result.optional_skipped,cv_uploaded=result.cv_uploaded,cover_letter_uploaded=result.cover_letter_uploaded,submitted=result.status in {"AUTO_SUBMITTED","SUBMISSION_UNVERIFIED"},submission_verified=result.status=="AUTO_SUBMITTED",submission_evidence=result.confirmation_text or result.confirmation_url,blocked_reason=result.message if result.status in {"MANUAL_REQUIRED","HUMAN_VERIFICATION","FAILED","UNKNOWN"} else "")
    path=diagnostics.save(); return replace(result,report_path=str(path))

class BrowserApplicationEngine:
    def __init__(self,profile:ApplicantProfile,state_callback:StateCallback|None=None,human_action_callback:HumanActionCallback|None=None,job_context:str="")->None:
        self.profile=profile; self.state_callback=state_callback; self.human_action_callback=human_action_callback; self.job_context=job_context
    def apply(self,url:str,job_id:int)->AutomationResult:
        blocked=_blocked_domain(url)
        if blocked: return _write_diagnostics(url,job_id,AutomationResult("SKIPPED_SOURCE",f"Browser launch blocked for {blocked}.","",0))
        if sync_playwright is None: return _write_diagnostics(url,job_id,AutomationResult("FAILED","Playwright is not installed. Run install.bat first.","",0))
        first=self._apply_once(url,job_id,0); recoverable=first.status=="FAILED" and any(m in first.message.lower() for m in ("targetclosederror","browser has been closed","page was closed")); result=self._apply_once(url,job_id,1) if recoverable else first; return _write_diagnostics(url,job_id,result)
    def _workday_checkpoint(self,page,screenshot,total_filled,adapter,registry):
        gate=detect_workday_gate(page)
        if not gate.blocked: return None
        return _manual_checkpoint(page,screenshot,gate.reason,total_filled,"MANUAL_REQUIRED",gate.reason,adapter,self.state_callback,registry,self.human_action_callback)
    def _apply_once(self,url,job_id,attempt):
        AUTOMATION_SCREENSHOT_DIR.mkdir(parents=True,exist_ok=True); BROWSER_PROFILE_DIR.mkdir(parents=True,exist_ok=True); screenshot=AUTOMATION_SCREENSHOT_DIR/f"job_{job_id}_attempt_{attempt+1}.png"; submit_started=False
        with sync_playwright() as playwright:
            context=playwright.chromium.launch_persistent_context(user_data_dir=str(BROWSER_PROFILE_DIR),headless=AUTOMATION_HEADLESS,viewport={"width":1440,"height":1000},accept_downloads=True); page=context.pages[0] if context.pages else context.new_page(); registry=PageRegistry(context)
            try:
                page.goto(url,wait_until="domcontentloaded",timeout=60_000); page=_open_application_form(page,registry); adapter=adapter_for_url(page.url or url); gate=self._workday_checkpoint(page,screenshot,0,adapter,registry)
                if gate: return gate
                verification=_detect_human_verification(page)
                if verification.blocked: return AutomationResult("SKIPPED_SOURCE","Security verification detected.","",0)
                total=0; fill_result=None
                for _ in range(4):
                    fill_result=fill_application_form(page,self.profile,adapter.final_submit_texts,job_context=self.job_context); total += fill_result.filled
                    if fill_result.restricted_questions: return _manual_checkpoint(page,screenshot,"Employer requires your own words.",total,"MANUAL_REQUIRED","Restricted questions remain.",adapter,self.state_callback,registry,self.human_action_callback)
                    if fill_result.required_unanswered: return _manual_checkpoint(page,screenshot,"Required questions remain.",total,"READY_TO_REVIEW","Required questions remain.",adapter,self.state_callback,registry,self.human_action_callback)
                    if fill_result.safe_submit_found: break
                    if not fill_result.next_step_found or not click_next_step(page): break
                    _wait_after_action(page)
                _screenshot(page,screenshot)
                if not fill_result or not fill_result.safe_submit_found: return AutomationResult("READY_TO_REVIEW","Final submit control not safely detected.",str(screenshot),total)
                if not adapter.auto_submit_allowed or not AUTOMATION_AUTO_SUBMIT_STANDARD_FORMS: return AutomationResult("READY_TO_REVIEW","Application ready for manual submission.",str(screenshot),total)
                submit_started=True
                if not click_safe_submit(page,adapter.final_submit_texts): return AutomationResult("UNKNOWN","Final control changed before click.",str(screenshot),total)
                _wait_after_action(page); _screenshot(page,screenshot); confirmation=_confirmation(page,adapter)
                if confirmation: return AutomationResult("AUTO_SUBMITTED",f"Application submitted through {adapter.name}.",str(screenshot),total,page.url,confirmation)
                return AutomationResult("UNKNOWN","Submission confirmation was not detected. Do not retry automatically.",str(screenshot),total)
            except PlaywrightTimeoutError:
                return AutomationResult("UNKNOWN" if submit_started else "FAILED","Page timed out.",str(screenshot),0)
            except Exception as exc:
                return AutomationResult("UNKNOWN" if submit_started else "FAILED",f"{type(exc).__name__}: {exc}",str(screenshot),0)
            finally: context.close()

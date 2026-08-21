from pathlib import Path

from automation.ats import adapter_for_url
from automation.browser import AutomationResult, BrowserApplicationEngine, PlaywrightTimeoutError, _blocked_domain, _detect_human_verification, _emit, _manual_checkpoint, _open_application_form, _screenshot, _wait_after_action, click_next_step, click_safe_submit, fill_application_form, sync_playwright
from automation.browser_hardening import inspect_browser_state, wait_for_submission_confirmation
from automation.forms import FillResult
from automation.page_registry import PageRegistry
from config.settings import AUTOMATION_AUTO_SUBMIT_STANDARD_FORMS, AUTOMATION_HEADLESS, AUTOMATION_SCREENSHOT_DIR, BROWSER_PROFILE_DIR

class HardenedBrowserApplicationEngine(BrowserApplicationEngine):
    """Production browser engine with explicit account/challenge/submission states."""
    def _checkpoint_state(self,page,screenshot:Path,total_filled:int,adapter,registry):
        state=inspect_browser_state(page)
        if state.human_challenge:return _manual_checkpoint(page,screenshot,"Human verification is required before VOCANTA can continue.",total_filled,"HUMAN_VERIFICATION",state.reason+". The application was not submitted.",adapter,self.state_callback,registry,self.human_action_callback)
        if state.account_required:return _manual_checkpoint(page,screenshot,"The employer requires account or email verification before VOCANTA can continue.",total_filled,"MANUAL_REQUIRED",state.reason+". The application was not submitted.",adapter,self.state_callback,registry,self.human_action_callback)
        return None
    def _apply_once(self,url:str,job_id:int,attempt:int)->AutomationResult:
        AUTOMATION_SCREENSHOT_DIR.mkdir(parents=True,exist_ok=True);BROWSER_PROFILE_DIR.mkdir(parents=True,exist_ok=True);screenshot=AUTOMATION_SCREENSHOT_DIR/f"job_{job_id}_attempt_{attempt+1}.png";submit_started=False
        with sync_playwright() as playwright:
            context=playwright.chromium.launch_persistent_context(user_data_dir=str(BROWSER_PROFILE_DIR),headless=AUTOMATION_HEADLESS,viewport={"width":1440,"height":1000},accept_downloads=True);page=context.pages[0] if context.pages else context.new_page();registry=PageRegistry(context)
            try:
                page.goto(url,wait_until="domcontentloaded",timeout=60_000);redirected=_blocked_domain(page.url or url)
                if redirected:return AutomationResult("SKIPPED_SOURCE",f"Redirected to disabled source {redirected}.","",0)
                page=_open_application_form(page,registry);adapter=adapter_for_url(page.url or url)
                workday_gate=self._workday_checkpoint(page,screenshot,0,adapter,registry)
                if workday_gate:return workday_gate
                state_gate=self._checkpoint_state(page,screenshot,0,adapter,registry)
                if state_gate:return state_gate
                verification=_detect_human_verification(page)
                if verification.blocked:
                    reason="; ".join(verification.reasons);_emit(self.state_callback,"BLOCKED",last_error=reason,active_url=str(page.url or url));return AutomationResult("SKIPPED_SOURCE",f"Security verification detected before form completion: {reason}.","",0)
                total_filled=0;fill_result:FillResult|None=None
                for _ in range(4):
                    fill_result=fill_application_form(page,self.profile,adapter.final_submit_texts,job_context=self.job_context);total_filled+=fill_result.filled
                    if fill_result.restricted_questions:
                        questions="; ".join(fill_result.restricted_questions[:6]);return _manual_checkpoint(page,screenshot,"Employer requires your own words for: "+questions,total_filled,"MANUAL_REQUIRED","AI-restricted questions require your personal response. The application was not submitted.",adapter,self.state_callback,registry,self.human_action_callback)
                    _emit(self.state_callback,"FORM_FILLED",active_url=str(page.url or ""))
                    if fill_result.required_unanswered:
                        fields="; ".join(fill_result.required_unanswered[:8]);return _manual_checkpoint(page,screenshot,"Employer-specific required questions need your answer:\n"+fields,total_filled,"READY_TO_REVIEW","Required questions remain or submission confirmation was not detected.",adapter,self.state_callback,registry,self.human_action_callback)
                    if fill_result.safe_submit_found:break
                    if not fill_result.next_step_found:break
                    before=registry.snapshot()
                    if not click_next_step(page):break
                    page=registry.after_action(page,before);_wait_after_action(page);workday_gate=self._workday_checkpoint(page,screenshot,total_filled,adapter,registry)
                    if workday_gate:return workday_gate
                    state_gate=self._checkpoint_state(page,screenshot,total_filled,adapter,registry)
                    if state_gate:return state_gate
                _screenshot(page,screenshot)
                if not fill_result or not fill_result.safe_submit_found:return _manual_checkpoint(page,screenshot,"VOCANTA filled the available fields but could not safely identify the final submission control.",total_filled,"READY_TO_REVIEW","Application is prepared for review. A verified final submit control was not detected.",adapter,self.state_callback,registry,self.human_action_callback)
                if not adapter.auto_submit_allowed or not AUTOMATION_AUTO_SUBMIT_STANDARD_FORMS:return _manual_checkpoint(page,screenshot,"The application is ready for final review.",total_filled,"READY_TO_REVIEW","Application remains ready for manual submission.",adapter,self.state_callback,registry,self.human_action_callback)
                state_gate=self._checkpoint_state(page,screenshot,total_filled,adapter,registry)
                if state_gate:return state_gate
                _emit(self.state_callback,"SUBMITTING",screenshot=str(screenshot),active_url=str(page.url or ""));submit_started=True;before=registry.snapshot()
                if not click_safe_submit(page,adapter.final_submit_texts):
                    _emit(self.state_callback,"UNKNOWN",screenshot=str(screenshot),last_error="Final submit control changed before click.",active_url=str(page.url or ""));return AutomationResult("UNKNOWN","The final control changed after submission was armed. Review before any retry.",str(screenshot),total_filled)
                page=registry.after_action(page,before);_emit(self.state_callback,"SUBMITTED",screenshot=str(screenshot),active_url=str(page.url or ""));_wait_after_action(page);_screenshot(page,screenshot);state=wait_for_submission_confirmation(page,timeout_ms=10_000)
                if state.submitted:
                    confirmation_url=str(page.url or "");_emit(self.state_callback,"CONFIRMED",screenshot=str(screenshot),confirmation_url=confirmation_url,confirmation_text=state.reason,active_url=confirmation_url);return AutomationResult("AUTO_SUBMITTED",f"Application submitted through {adapter.name}.",str(screenshot),total_filled,confirmation_url,state.reason,adapter.final_submit_texts[0],fill_result.fields_detected,fill_result.required_fields,0,fill_result.optional_skipped,fill_result.cv_uploaded,fill_result.cover_letter_uploaded)
                if state.human_challenge:return _manual_checkpoint(page,screenshot,"Human verification appeared during submission.",total_filled,"UNKNOWN","Submission was not confirmed because human verification remains unresolved.",adapter,self.state_callback,registry,self.human_action_callback)
                if state.account_required:return _manual_checkpoint(page,screenshot,"Account or email verification appeared during submission.",total_filled,"UNKNOWN","Submission was not confirmed because account verification remains unresolved.",adapter,self.state_callback,registry,self.human_action_callback)
                return _manual_checkpoint(page,screenshot,"VOCANTA clicked the final control, but the employer did not show a recognised confirmation.",total_filled,"UNKNOWN","Submission confirmation was not detected. Review before any retry to avoid a duplicate application.",adapter,self.state_callback,registry,self.human_action_callback)
            except PlaywrightTimeoutError:
                status="UNKNOWN" if submit_started else "FAILED";message="The page timed out after submission began. Do not retry automatically." if submit_started else "The application page timed out.";_emit(self.state_callback,status,screenshot=str(screenshot),last_error=message,active_url=str(getattr(page,"url","") or ""));return AutomationResult(status,message,str(screenshot),0)
            except Exception as exc:
                status="UNKNOWN" if submit_started else "FAILED";message=f"{type(exc).__name__}: {exc}";_emit(self.state_callback,status,screenshot=str(screenshot),last_error=message,active_url=str(getattr(page,"url","") or ""));return AutomationResult(status,message,str(screenshot),0)
            finally:context.close()

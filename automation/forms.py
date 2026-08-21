from dataclasses import dataclass
import logging
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from playwright.sync_api import Frame, Locator, Page
else:
    Frame = Locator = Page = Any

from automation.profile import ApplicantProfile
from automation.cv_knowledge import answer_from_cv
from automation.questions import Intent, identify_intent, normalize, resolve_question, restriction_reason
from automation.diagnostics import FieldAudit

logger = logging.getLogger(__name__)

@dataclass(frozen=True, slots=True)
class FillResult:
    filled: int
    required_unanswered: tuple[str, ...]
    safe_submit_found: bool
    next_step_found: bool
    action_audit: tuple[str, ...] = ()
    restricted_questions: tuple[str, ...] = ()
    fields_detected: int = 0
    required_fields: int = 0
    optional_skipped: int = 0
    cv_uploaded: bool = False
    cover_letter_uploaded: bool = False
    field_audit: tuple[FieldAudit, ...] = ()

FIELD_ALIASES = {"first_name":("first name","firstname","given name","given-name"),"middle_name":("middle name","middlename","middle initial","additional name"),"last_name":("last name","lastname","surname","family name","family-name"),"full_name":("full name","your name","candidate name"),"email":("email","email address","e-mail"),"phone":("phone","phone number","mobile","telephone","contact number"),"city":("city","current city","location city"),"country":("country","current country","country of residence"),"address":("address","street address","home address"),"postal_code":("postal code","postcode","zip code","zip"),"linkedin_url":("linkedin","linkedin profile","linkedin url"),"website_url":("website","portfolio","personal website"),"notice_period":("notice period","availability","when can you start"),"salary_expectation":("salary expectation","expected salary","desired salary","compensation expectation")}
FINAL_SUBMIT_TEXTS=("submit application","send application","complete application","finish application","confirm and submit","submit")
NEXT_STEP_TEXTS=("continue","next","save and continue","proceed","review application","review and submit")
NEGATIVE_BUTTON_TEXTS=("cancel","back","close","delete","withdraw","save job")

def normalize(value:str|None)->str: return " ".join((value or "").lower().split())
def profile_value(profile,field,*,has_middle_name_field):
    if field=="full_name": return profile.full_name
    if field=="last_name" and not has_middle_name_field: return profile.employer_last_name
    return str(getattr(profile,field,"") or "")
def identify_field(label):
    intent=identify_intent(label); return {Intent.FIRST_NAME:"first_name",Intent.MIDDLE_NAME:"middle_name",Intent.LAST_NAME:"last_name",Intent.FULL_NAME:"full_name",Intent.EMAIL:"email",Intent.PHONE:"phone",Intent.CITY:"city",Intent.CURRENT_COUNTRY:"country",Intent.ADDRESS:"address",Intent.POSTAL_CODE:"postal_code",Intent.LINKEDIN:"linkedin_url",Intent.WEBSITE:"website_url",Intent.NOTICE_PERIOD:"notice_period",Intent.SALARY:"salary_expectation"}.get(intent)
def form_frames(page):
    frames=[page.main_frame]+[f for f in page.frames if f!=page.main_frame]; unique=[]; seen=set()
    for frame in frames:
        if id(frame) not in seen: seen.add(id(frame)); unique.append(frame)
    return tuple(unique)
def _label_for(locator):
    locator_id=locator.get_attribute("id")
    if locator_id:
        label=locator.page.locator(f'label[for="{locator_id}"]')
        if label.count():
            try:return label.first.inner_text()
            except Exception:pass
    for attribute in ("aria-label","placeholder","name","autocomplete","data-qa","data-testid","id"):
        value=locator.get_attribute(attribute)
        if value:return value
    try:return locator.locator("xpath=..").inner_text()[:500]
    except Exception:return ""
def _has_middle_name_field(frame):
    controls=frame.locator('input:not([type="hidden"]):not([type="file"]):not([type="submit"]), textarea')
    for i in range(controls.count()):
        try:
            if identify_field(_label_for(controls.nth(i)))=="middle_name":return True
        except Exception:continue
    return False
def _fill_text_inputs(frame,profile,job_context=""):
    filled=0; has_middle=_has_middle_name_field(frame); controls=frame.locator('input:not([type="hidden"]):not([type="file"]):not([type="submit"]):not([type="button"]):not([type="checkbox"]):not([type="radio"]), textarea')
    for i in range(controls.count()):
        control=controls.nth(i)
        try:
            if not control.is_visible() or control.is_disabled() or control.input_value().strip():continue
            label=_label_for(control); field=identify_field(label); value=profile_value(profile,field,has_middle_name_field=has_middle) if field else ""; source=f"profile.{field}" if field else ""
            if not value:
                grounded=answer_from_cv(label,profile,job_context=job_context)
                if grounded:value=grounded.value;source=grounded.source
            if not value:continue
            control.fill(value);filled+=1;logger.info("Grounded field fill | label=%r | source=%s",label[:180],source)
        except Exception:continue
    return filled
def _upload_documents(frame,profile):
    uploaded=0;files=frame.locator('input[type="file"]')
    for i in range(files.count()):
        c=files.nth(i);label=normalize(_label_for(c))
        try:
            if any(t in label for t in ("cover","letter")) and profile.cover_letter_path:c.set_input_files(profile.cover_letter_path);uploaded+=1
            elif any(t in label for t in ("certificate","supporting","additional document","other document")) and profile.supporting_document_path:c.set_input_files(profile.supporting_document_path);uploaded+=1
            elif profile.resume_path:c.set_input_files(profile.resume_path);uploaded+=1
        except Exception:continue
    return uploaded
def _select_by_visible_text(select,preferred):
    for label in (preferred,preferred.lower(),preferred.upper()):
        try:select.select_option(label=label);return True
        except Exception:continue
    options=select.locator("option")
    for i in range(options.count()):
        option=options.nth(i)
        try:
            text=normalize(option.inner_text())
            if normalize(preferred) in text or text in normalize(preferred):
                value=option.get_attribute("value")
                if value is not None:select.select_option(value=value);return True
        except Exception:continue
    return False
def _select_common_options(frame,profile):
    filled=0;selects=frame.locator("select")
    for i in range(selects.count()):
        s=selects.nth(i)
        try:
            if not s.is_visible() or s.is_disabled():continue
            label=normalize(_label_for(s));success=False
            if "country" in label:success=_select_by_visible_text(s,profile.country)
            elif "sponsor" in label or "visa" in label:success=_select_by_visible_text(s,"Yes" if profile.requires_sponsorship else "No")
            elif "work authorization" in label or "authorisation" in label:success=_select_by_visible_text(s,profile.work_authorization)
            if success:filled+=1
        except Exception:continue
    return filled
def _required_unanswered(frame):
    unanswered=[];controls=frame.locator('input[required]:not([type="hidden"]), textarea[required], select[required], input[aria-required="true"]:not([type="hidden"]), textarea[aria-required="true"], select[aria-required="true"]')
    for i in range(controls.count()):
        c=controls.nth(i)
        try:
            if not c.is_visible() or c.is_disabled():continue
            tag=c.evaluate("(node)=>node.tagName.toLowerCase()");typ=normalize(c.get_attribute("type"));answered=True
            if tag=="select":answered=bool(c.input_value())
            elif typ in {"checkbox","radio"}:
                name=c.get_attribute("name");answered=frame.locator(f'input[name="{name}"]:checked').count()>0 if name else c.is_checked()
            elif typ=="file":answered=bool(c.input_value())
            else:answered=bool(c.input_value().strip())
            if not answered:unanswered.append(" ".join((_label_for(c) or c.get_attribute("name") or "Unknown field").split())[:180])
        except Exception:continue
    return unanswered
def _control_text(control):
    for a in ("value","aria-label","title","name","data-testid"):
        v=control.get_attribute(a)
        if v:return normalize(v)
    try:return normalize(control.inner_text())
    except Exception:return ""
def _candidate_controls(frame):return frame.locator('button, input[type="submit"], input[type="button"], a[role="button"], div[role="button"]')
def audit_action_controls(page,texts,*,exact=False):
    entries=[]
    for fi,frame in enumerate(form_frames(page)):
        controls=_candidate_controls(frame)
        for i in range(controls.count()):
            c=controls.nth(i)
            try:
                text=_control_text(c);visible=c.is_visible();enabled=c.is_enabled();negative=bool(text and any(t in text for t in NEGATIVE_BUTTON_TEXTS));matched=bool(text) and (any(text==t for t in texts) if exact else any(text==t or t in text for t in texts));entries.append(f"frame={fi} index={i} text={text!r} visible={visible} enabled={enabled} negative={negative} matched={matched}")
            except Exception as exc:entries.append(f"frame={fi} index={i} inspection_error={type(exc).__name__}: {exc}")
    return tuple(entries or ["no candidate action controls found"])
def find_action_control(page,texts,*,exact=False):
    for frame in form_frames(page):
        controls=_candidate_controls(frame)
        for i in range(controls.count()):
            c=controls.nth(i)
            try:
                if not c.is_visible() or not c.is_enabled():continue
                text=_control_text(c)
                if not text or any(t in text for t in NEGATIVE_BUTTON_TEXTS):continue
                if any(text==t for t in texts) if exact else any(text==t or t in text for t in texts):return frame,c
            except Exception:continue
    return None
def click_safe_submit(page,texts=FINAL_SUBMIT_TEXTS):
    result=find_action_control(page,texts,exact=True)
    if not result:return False
    _,c=result;c.scroll_into_view_if_needed();c.click();return True
def click_next_step(page):
    result=find_action_control(page,NEXT_STEP_TEXTS)
    if not result:return False
    _,c=result;c.scroll_into_view_if_needed();c.click();return True
def _is_required(c):return bool(c.get_attribute("required") is not None or normalize(c.get_attribute("aria-required"))=="true")
def _choose_radio_or_checkbox(frame,profile):
    filled=0;audits=[];restricted=[];groups=set();controls=frame.locator('input[type="radio"], input[type="checkbox"]')
    for i in range(controls.count()):
        c=controls.nth(i)
        try:
            if not c.is_visible() or c.is_disabled() or c.is_checked():continue
            name=c.get_attribute("name") or f"__single_{i}"
            if name in groups:continue
            groups.add(name);label=_label_for(c);group=frame.locator(f'input[name="{name}"]') if not name.startswith('__single_') else c;combined=label
            if group.count()>1:
                try:combined=group.first.locator("xpath=../..").inner_text()[:500]
                except Exception:pass
            restriction=restriction_reason(combined)
            if restriction:restricted.append(combined.strip()[:220]);audits.append(FieldAudit(combined[:180],identify_intent(combined).value,_is_required(c),"blocked",restriction));continue
            resolution=resolve_question(combined,profile)
            if not resolution.value:continue
            desired=normalize(resolution.value);chosen=None
            for oi in range(group.count()):
                option=group.nth(oi);option_label=normalize(_label_for(option));option_value=normalize(option.get_attribute("value"))
                if desired==option_label or desired==option_value or desired in option_label:chosen=option;break
            if chosen is not None:chosen.check(force=True);filled+=1;audits.append(FieldAudit(combined[:180],identify_intent(combined).value,_is_required(c),"filled",resolution.source))
        except Exception:continue
    return filled,audits,restricted
def fill_application_form(page:Page,profile:ApplicantProfile,final_submit_texts:tuple[str,...]=FINAL_SUBMIT_TEXTS,*,job_context:str="")->FillResult:
    filled=0;unanswered=[];audits=[];restricted=[];detected=0;required=0
    for frame in form_frames(page):
        detected+=frame.locator('input, textarea, select').count();required+=frame.locator('[required], [aria-required="true"]').count();filled+=_fill_text_inputs(frame,profile,job_context);filled+=_upload_documents(frame,profile);filled+=_select_common_options(frame,profile);rf,ra,rr=_choose_radio_or_checkbox(frame,profile);filled+=rf;audits.extend(ra);restricted.extend(rr);unanswered.extend(_required_unanswered(frame))
    submit=find_action_control(page,final_submit_texts,exact=True);next_step=find_action_control(page,NEXT_STEP_TEXTS)
    return FillResult(filled,tuple(dict.fromkeys(unanswered)),submit is not None,next_step is not None,audit_action_controls(page,final_submit_texts,exact=True),tuple(dict.fromkeys(restricted)),detected,required,field_audit=tuple(audits))

from dataclasses import dataclass
import logging
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from playwright.sync_api import Page
else:
    Page = Any

from automation.profile import ApplicantProfile
from automation.questions import Intent, identify_intent, normalize, resolve_question
from automation.semantic_answers import answer_application_question
from automation.diagnostics import FieldAudit
from core.text_rules import sanitize_applicant_text

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

FINAL_SUBMIT_TEXTS=("submit application","send application","complete application","finish application","confirm and submit","submit")
NEXT_STEP_TEXTS=("continue","next","save and continue","proceed","review application","review and submit")
NEGATIVE_BUTTON_TEXTS=("cancel","back","close","delete","withdraw","save job")

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
    try:
        parent=locator.locator("xpath=.."); text=parent.inner_text()
        if text:return text[:900]
    except Exception:pass
    try:return locator.locator("xpath=../..").inner_text()[:900]
    except Exception:return ""
def _has_middle_name_field(frame):
    controls=frame.locator('input:not([type="hidden"]):not([type="file"]):not([type="submit"]), textarea')
    for i in range(controls.count()):
        try:
            if identify_field(_label_for(controls.nth(i)))=="middle_name":return True
        except Exception:continue
    return False
def _fill_text_inputs(frame,profile,job_context=""):
    filled=0; audits=[]; has_middle=_has_middle_name_field(frame); controls=frame.locator('input:not([type="hidden"]):not([type="file"]):not([type="submit"]):not([type="button"]):not([type="checkbox"]):not([type="radio"]), textarea')
    for i in range(controls.count()):
        control=controls.nth(i)
        try:
            if not control.is_visible() or control.is_disabled() or control.input_value().strip():continue
            label=_label_for(control); field=identify_field(label); value=profile_value(profile,field,has_middle_name_field=has_middle) if field else ""; source=f"profile.{field}" if field else ""
            if not value:
                grounded=answer_application_question(label,profile,job_context=job_context)
                if grounded:value=grounded.value;source=grounded.source
            if not value:continue
            value=sanitize_applicant_text(value); control.fill(value); filled+=1
            audits.append(FieldAudit(label[:180],identify_intent(label).value,_is_required(control),"filled",source or "cv semantic evidence"))
            logger.info("Grounded field fill | label=%r | source=%s",label[:180],source)
        except Exception:continue
    return filled,audits
def _upload_documents(frame,profile):
    uploaded=0;cv=False;cover=False;files=frame.locator('input[type="file"]')
    for i in range(files.count()):
        c=files.nth(i);label=normalize(_label_for(c))
        try:
            if any(t in label for t in ("cover","letter")) and profile.cover_letter_path:
                c.set_input_files(profile.cover_letter_path);uploaded+=1;cover=True
            elif any(t in label for t in ("certificate","supporting","additional document","other document")) and profile.supporting_document_path:
                c.set_input_files(profile.supporting_document_path);uploaded+=1
            elif profile.resume_path:
                c.set_input_files(profile.resume_path);uploaded+=1;cv=True
        except Exception:continue
    return uploaded,cv,cover
def _select_by_visible_text(select,preferred):
    if not preferred:return False
    for label in (preferred,preferred.lower(),preferred.upper()):
        try:select.select_option(label=label);return True
        except Exception:continue
    options=select.locator("option"); target=normalize(preferred)
    for i in range(options.count()):
        option=options.nth(i)
        try:
            text=normalize(option.inner_text())
            if target==text or target in text or (text and text in target):
                value=option.get_attribute("value")
                if value is not None:select.select_option(value=value);return True
        except Exception:continue
    return False
def _preferred_answer(label,profile,job_context=""):
    resolution=resolve_question(label,profile)
    if resolution.value and resolution.auto_fill_allowed:return resolution.value,resolution.reason or f"profile.{resolution.intent.value.lower()}"
    grounded=answer_application_question(label,profile,job_context=job_context)
    return (grounded.value,grounded.source) if grounded else ("","")
def _select_common_options(frame,profile,job_context=""):
    filled=0;audits=[];selects=frame.locator("select")
    for i in range(selects.count()):
        s=selects.nth(i)
        try:
            if not s.is_visible() or s.is_disabled():continue
            current=normalize(s.input_value())
            if current and current not in {"select","choose","please select"}:continue
            label=_label_for(s);preferred,source=_preferred_answer(label,profile,job_context)
            if preferred and _select_by_visible_text(s,preferred):
                filled+=1;audits.append(FieldAudit(label[:180],identify_intent(label).value,_is_required(s),"filled",source))
        except Exception:continue
    return filled,audits
def _fill_custom_comboboxes(frame,profile,job_context=""):
    filled=0;audits=[];boxes=frame.locator('[role="combobox"]:not(select)')
    for i in range(boxes.count()):
        box=boxes.nth(i)
        try:
            if not box.is_visible() or box.is_disabled():continue
            label=_label_for(box);preferred,source=_preferred_answer(label,profile,job_context)
            if not preferred:continue
            box.click(); box.page.wait_for_timeout(150)
            option=frame.get_by_role("option",name=preferred,exact=True)
            if not option.count(): option=frame.get_by_role("option",name=preferred,exact=False)
            if option.count():
                option.first.click();filled+=1;audits.append(FieldAudit(label[:180],identify_intent(label).value,_is_required(box),"filled",source))
        except Exception:continue
    return filled,audits
def _required_unanswered(frame):
    unanswered=[];controls=frame.locator('input[required]:not([type="hidden"]), textarea[required], select[required], [role="combobox"][aria-required="true"], input[aria-required="true"]:not([type="hidden"]), textarea[aria-required="true"], select[aria-required="true"]')
    for i in range(controls.count()):
        c=controls.nth(i)
        try:
            if not c.is_visible() or c.is_disabled():continue
            tag=c.evaluate("(node)=>node.tagName.toLowerCase()");typ=normalize(c.get_attribute("type"));answered=True
            if tag=="select":answered=bool(c.input_value())
            elif c.get_attribute("role")=="combobox":answered=normalize(c.get_attribute("aria-expanded"))!="" and normalize(c.inner_text()) not in {"","select","choose"}
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
def _choose_radio_or_checkbox(frame,profile,job_context=""):
    filled=0;audits=[];groups=set();controls=frame.locator('input[type="radio"], input[type="checkbox"]')
    for i in range(controls.count()):
        c=controls.nth(i)
        try:
            if not c.is_visible() or c.is_disabled() or c.is_checked():continue
            name=c.get_attribute("name") or f"__single_{i}"
            if name in groups:continue
            groups.add(name);label=_label_for(c);group=frame.locator(f'input[name="{name}"]') if not name.startswith('__single_') else c;combined=label
            if group.count()>1:
                try:combined=group.first.locator("xpath=../..").inner_text()[:900]
                except Exception:pass
            desired,source=_preferred_answer(combined,profile,job_context);desired=normalize(desired)
            if not desired:continue
            chosen=None
            for oi in range(group.count()):
                option=group.nth(oi);option_label=normalize(_label_for(option));option_value=normalize(option.get_attribute("value"))
                if desired==option_label or desired==option_value or desired in option_label:chosen=option;break
            if chosen is not None:chosen.check(force=True);filled+=1;audits.append(FieldAudit(combined[:180],identify_intent(combined).value,_is_required(c),"filled",source or "grounded semantic answer"))
        except Exception:continue
    return filled,audits
def fill_application_form(page:Page,profile:ApplicantProfile,final_submit_texts:tuple[str,...]=FINAL_SUBMIT_TEXTS,*,job_context:str="")->FillResult:
    filled=0;unanswered=[];audits=[];detected=0;required=0;cv_uploaded=False;cover_uploaded=False
    for frame in form_frames(page):
        detected+=frame.locator('input, textarea, select, [role="combobox"]').count();required+=frame.locator('[required], [aria-required="true"]').count()
        n,a=_fill_text_inputs(frame,profile,job_context);filled+=n;audits.extend(a)
        n,cv,cover=_upload_documents(frame,profile);filled+=n;cv_uploaded=cv_uploaded or cv;cover_uploaded=cover_uploaded or cover
        n,a=_select_common_options(frame,profile,job_context);filled+=n;audits.extend(a)
        n,a=_fill_custom_comboboxes(frame,profile,job_context);filled+=n;audits.extend(a)
        n,a=_choose_radio_or_checkbox(frame,profile,job_context);filled+=n;audits.extend(a)
        unanswered.extend(_required_unanswered(frame))
    submit=find_action_control(page,final_submit_texts,exact=True);next_step=find_action_control(page,NEXT_STEP_TEXTS)
    return FillResult(filled,tuple(dict.fromkeys(unanswered)),submit is not None,next_step is not None,audit_action_controls(page,final_submit_texts,exact=True),(),detected,required,cv_uploaded=cv_uploaded,cover_letter_uploaded=cover_uploaded,field_audit=tuple(audits))

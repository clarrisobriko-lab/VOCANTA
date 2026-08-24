from __future__ import annotations

import re
from typing import Any

from automation.forms import FillResult, FINAL_SUBMIT_TEXTS, fill_application_form, find_action_control, normalize
from automation.profile import ApplicantProfile


def _text(locator: Any) -> str:
    parts: list[str] = []
    for attr in ("aria-label", "placeholder", "name", "data-testid", "id"):
        try:
            value = locator.get_attribute(attr)
            if value: parts.append(value)
        except Exception: pass
    for depth in range(1, 6):
        try:
            value = normalize(locator.locator(f"xpath=ancestor::div[{depth}]").inner_text(timeout=250))
            if value and len(value) <= 700: parts.append(value)
        except Exception: pass
    return normalize(" ".join(parts))


def _nearby_text(control: Any) -> str:
    candidates: list[str] = []
    for depth in range(1, 7):
        try:
            text = normalize(control.locator(f"xpath=ancestor::div[{depth}]").inner_text(timeout=200))
            if text and len(text) <= 900: candidates.append(text)
        except Exception: pass
    return min(candidates, key=len) if candidates else _text(control)


def _ashby_upload(page: Any, profile: ApplicantProfile) -> tuple[int, bool, bool]:
    uploaded = 0; cv = cover = False; files = page.locator('input[type="file"]')
    for index in range(files.count()):
        control = files.nth(index)
        try:
            label = _text(control)
            if control.input_value(): continue
            if "cover letter" in label and profile.cover_letter_path:
                control.set_input_files(profile.cover_letter_path); uploaded += 1; cover = True
            elif not cv and profile.resume_path:
                control.set_input_files(profile.resume_path); uploaded += 1; cv = True
        except Exception: continue
    return uploaded, cv, cover


def _hourly_rate(profile: ApplicantProfile) -> str:
    raw = str(profile.salary_expectation or "7")
    values = [float(x) for x in re.findall(r"\d+(?:\.\d+)?", raw.replace(",", ""))]
    valid = [x for x in values if 3.5 <= x <= 7.0]; value = max(valid) if valid else 7.0
    return str(int(value)) if value.is_integer() else str(value)


def _answer_for(label: str, profile: ApplicantProfile) -> str:
    label = normalize(label)
    if "introductory video" in label: return profile.standard_answers.get("introductory_video_url", "")
    if "how did you hear about this job opening" in label: return profile.standard_answers.get("how_did_you_hear", "LinkedIn")
    if "target hourly rate" in label: return _hourly_rate(profile)
    if "when are you looking to start" in label or "notice period" in label: return profile.notice_period
    if "linkedin profile" in label: return profile.linkedin_url
    if label.startswith("name") and "email" not in label: return profile.full_name
    if "first name" in label: return profile.first_name
    if "last name" in label: return profile.employer_last_name
    if label.startswith("email"): return profile.email
    if label.startswith("phone"): return profile.phone
    if "website" in label: return profile.website_url
    return ""


def _fill_named(page: Any, label: str, value: str) -> int:
    if not value: return 0
    for exact in (True, False):
        try:
            control = page.get_by_label(label, exact=exact).first
            if control.count() and control.is_visible() and not control.is_disabled():
                current = control.input_value().strip()
                if current != str(value): control.fill(str(value))
                return 1
        except Exception: pass
    return 0


def _fill_by_question(page: Any, fragment: str, value: str) -> int:
    controls = page.locator('input:not([type="hidden"]):not([type="file"]):not([type="checkbox"]):not([type="radio"]), textarea')
    for index in range(controls.count()):
        control = controls.nth(index)
        try:
            if not control.is_visible() or control.is_disabled(): continue
            if fragment.lower() not in _nearby_text(control).lower(): continue
            if control.input_value().strip() != str(value): control.fill(str(value))
            return 1
        except Exception: continue
    return 0


def _ashby_fill_text(page: Any, profile: ApplicantProfile) -> int:
    filled = 0
    direct = (("Name", profile.full_name), ("How did you hear about this job opening?", profile.standard_answers.get("how_did_you_hear", "LinkedIn")), ("When are you looking to start?", profile.notice_period), ("LinkedIn Profile", profile.linkedin_url))
    for label, value in direct: filled += _fill_named(page, label, value)
    filled += _fill_by_question(page, "target hourly rate", _hourly_rate(profile))
    controls = page.locator('input:not([type="hidden"]):not([type="file"]):not([type="checkbox"]):not([type="radio"]), textarea')
    for index in range(controls.count()):
        control = controls.nth(index)
        try:
            if not control.is_visible() or control.is_disabled() or control.input_value().strip(): continue
            value = _answer_for(_nearby_text(control), profile)
            if value: control.fill(str(value)); filled += 1
        except Exception: continue
    return filled


def _select_in_question(page: Any, question_fragment: str, answer: str) -> int:
    candidates = page.locator("div").filter(has_text=question_fragment); best = None; best_len = 10**9
    for index in range(min(candidates.count(), 50)):
        container = candidates.nth(index)
        try:
            text = normalize(container.inner_text(timeout=150))
            if question_fragment.lower() not in text.lower() or answer.lower() not in text.lower() or len(text) >= best_len: continue
            if container.get_by_text(answer, exact=True).count(): best, best_len = container, len(text)
        except Exception: continue
    if best is None: return 0
    try:
        radio = best.get_by_role("radio", name=answer, exact=True).first
        if radio.count(): radio.check(force=True); return 1 if radio.is_checked() else 0
    except Exception: pass
    try: best.get_by_text(answer, exact=True).first.click(force=True); page.wait_for_timeout(150); return 1
    except Exception: return 0


def _ashby_binary_answers(page: Any, profile: ApplicantProfile) -> int:
    filled = _select_in_question(page, "available for full time work", "Yes")
    filled += _select_in_question(page, "willingness to adhere to this schedule", "Yes")
    if profile.privacy_acknowledgements: filled += _select_in_question(page, "recruitment process includes questions", "Yes")
    return filled


def _ashby_location(page: Any, profile: ApplicantProfile) -> int:
    country = (profile.country or "Nigeria").strip(); controls = page.locator('[role="combobox"], input')
    for index in range(controls.count()):
        control = controls.nth(index)
        try:
            if not control.is_visible() or control.is_disabled(): continue
            question = _nearby_text(control).lower()
            if "location" not in question and "country" not in question: continue
            control.click(force=True); control.fill(""); control.fill(country); page.wait_for_timeout(800)
            options = page.locator('[role="option"]:visible'); chosen = None
            for oi in range(options.count()):
                option = options.nth(oi); text = normalize(option.inner_text(timeout=150))
                if text.lower() == country.lower(): chosen = option; break
            if chosen is None:
                for oi in range(options.count()):
                    option = options.nth(oi); text = normalize(option.inner_text(timeout=150))
                    if country.lower() in text.lower(): chosen = option; break
            if chosen is None: continue
            chosen.click(force=True); page.wait_for_timeout(350)
            if country.lower() in normalize(control.input_value()).lower(): return 1
        except Exception: continue
    return 0


def _manual_requirements(page: Any, profile: ApplicantProfile) -> list[str]:
    body = normalize(page.locator("body").inner_text(timeout=2000))
    if "3 to 5 minute introductory video" in body and not profile.standard_answers.get("introductory_video_url", "").strip(): return ["Introductory video link, 3 to 5 minutes, publicly viewable"]
    return []


def _required_unanswered(page: Any, profile: ApplicantProfile) -> list[str]:
    unresolved: list[str] = []; controls = page.locator('input:not([type="hidden"]):not([type="file"]), textarea, select')
    for index in range(controls.count()):
        control = controls.nth(index)
        try:
            if not control.is_visible() or control.is_disabled(): continue
            label = _nearby_text(control); required = control.get_attribute("required") is not None or control.get_attribute("aria-required") == "true" or "*" in label
            if not required: continue
            value = ""
            try: value = control.input_value().strip()
            except Exception: pass
            if value: continue
            candidate = normalize(label)
            if not candidate or candidate == "type here" or "systemfield name" in candidate: continue
            if candidate not in unresolved: unresolved.append(candidate)
        except Exception: continue
    for requirement in _manual_requirements(page, profile):
        if requirement not in unresolved: unresolved.append(requirement)
    return unresolved


def fill_ashby_application(page: Any, profile: ApplicantProfile, final_submit_texts: tuple[str, ...] = FINAL_SUBMIT_TEXTS, *, job_context: str = "") -> FillResult:
    generic = fill_application_form(page, profile, final_submit_texts, job_context=job_context)
    extra_filled = _ashby_fill_text(page, profile) + _ashby_binary_answers(page, profile) + _ashby_location(page, profile)
    upload_count, cv, cover = _ashby_upload(page, profile)
    detected = page.locator('input, textarea, select, [role="combobox"]').count(); submit = find_action_control(page, final_submit_texts, exact=True); unresolved = _required_unanswered(page, profile)
    return FillResult(filled=generic.filled + extra_filled + upload_count, required_unanswered=unresolved, safe_submit_found=submit is not None, next_step_found=generic.next_step_found, action_audit=generic.action_audit, restricted_questions=generic.restricted_questions, fields_detected=max(generic.fields_detected, detected), required_fields=max(generic.required_fields, len(unresolved)), optional_skipped=generic.optional_skipped, cv_uploaded=generic.cv_uploaded or cv, cover_letter_uploaded=generic.cover_letter_uploaded or cover, field_audit=generic.field_audit)

from __future__ import annotations

from typing import Any

from automation.forms import FillResult, FINAL_SUBMIT_TEXTS, fill_application_form, find_action_control, normalize
from automation.profile import ApplicantProfile


def _text(locator: Any) -> str:
    parts: list[str] = []
    for attr in ("aria-label", "placeholder", "name", "data-testid", "id"):
        try:
            value = locator.get_attribute(attr)
            if value:
                parts.append(value)
        except Exception:
            pass
    # Ashby inputs often have no useful label attributes. Walk upward through
    # several compact containers and prefer their visible question text.
    for depth in range(1, 6):
        try:
            value = locator.locator(f"xpath=ancestor::div[{depth}]").inner_text(timeout=250)
            value = normalize(value)
            if value and len(value) <= 700:
                parts.append(value)
        except Exception:
            pass
    return normalize(" ".join(parts))


def _ashby_upload(page: Any, profile: ApplicantProfile) -> tuple[int, bool, bool]:
    uploaded = 0
    cv = cover = False
    files = page.locator('input[type="file"]')
    for index in range(files.count()):
        control = files.nth(index)
        try:
            label = _text(control)
            if control.input_value():
                continue
            if "cover letter" in label and profile.cover_letter_path:
                control.set_input_files(profile.cover_letter_path)
                uploaded += 1
                cover = True
            elif not cv and profile.resume_path:
                control.set_input_files(profile.resume_path)
                uploaded += 1
                cv = True
        except Exception:
            continue
    return uploaded, cv, cover


def _answer_for(label: str, profile: ApplicantProfile) -> str:
    if "how did you hear" in label:
        return profile.standard_answers.get("how_did_you_hear", "")
    if "target hourly rate" in label:
        return profile.salary_expectation
    if "when are you looking to start" in label or "notice period" in label:
        return profile.notice_period
    if "linkedin profile" in label or "linkedin" in label:
        return profile.linkedin_url
    if "email" in label:
        return profile.email
    if "phone" in label:
        return profile.phone
    if "location" in label:
        return ""  # Ashby location is a suggestion-backed combobox, handled separately.
    # Match full Name only when this container is actually the Name question.
    compact = label.replace("type here", "").strip()
    if compact == "name*" or compact == "name" or compact.startswith("name* email"):
        return profile.full_name
    if "first name" in label:
        return profile.first_name
    if "last name" in label:
        return profile.employer_last_name
    if "website" in label:
        return profile.website_url
    return ""


def _ashby_fill_text(page: Any, profile: ApplicantProfile) -> int:
    filled = 0
    controls = page.locator('input:not([type="hidden"]):not([type="file"]):not([type="checkbox"]):not([type="radio"]), textarea')
    for index in range(controls.count()):
        control = controls.nth(index)
        try:
            if not control.is_visible() or control.is_disabled() or control.input_value().strip():
                continue
            value = _answer_for(_text(control), profile)
            if value:
                control.fill(str(value))
                filled += 1
        except Exception:
            continue
    return filled


def _ashby_location(page: Any, profile: ApplicantProfile) -> int:
    # Location requires choosing an Ashby suggestion rather than plain fill.
    controls = page.locator('[role="combobox"], input')
    for index in range(controls.count()):
        control = controls.nth(index)
        try:
            if not control.is_visible() or control.is_disabled() or control.input_value().strip():
                continue
            if "location" not in _text(control):
                continue
            control.fill(profile.current_location or f"{profile.city}, {profile.country}")
            page.wait_for_timeout(500)
            option = page.locator('[role="option"]:visible').first
            if option.count():
                option.click()
                return 1
        except Exception:
            continue
    return 0


def _manual_requirements(page: Any) -> list[str]:
    body = normalize(page.locator("body").inner_text(timeout=2000))
    requirements: list[str] = []
    if "3 to 5 minute introductory video" in body and "video" in body:
        requirements.append("Introductory video link, 3 to 5 minutes, publicly viewable")
    return requirements


def _clean_required(items: list[str]) -> list[str]:
    cleaned: list[str] = []
    for item in items:
        value = normalize(item)
        # Generic Ashby ids/placeholders are diagnostic noise, not questions.
        if not value or value == "type here" or "systemfield_name" in value:
            continue
        if value not in cleaned:
            cleaned.append(value)
    return cleaned


def _required_unanswered(page: Any, existing: list[str]) -> list[str]:
    unresolved = _clean_required(existing)
    controls = page.locator('input:not([type="hidden"]):not([type="file"]), textarea')
    for index in range(controls.count()):
        control = controls.nth(index)
        try:
            if not control.is_visible() or control.is_disabled() or control.input_value().strip():
                continue
            label = _text(control)
            required = control.get_attribute("required") is not None or control.get_attribute("aria-required") == "true" or "*" in label
            if required:
                candidate = label.replace("type here", "").strip()
                if candidate and len(candidate) <= 500 and candidate not in unresolved:
                    unresolved.append(candidate)
        except Exception:
            continue
    for requirement in _manual_requirements(page):
        if requirement not in unresolved:
            unresolved.append(requirement)
    return unresolved


def fill_ashby_application(page: Any, profile: ApplicantProfile, final_submit_texts: tuple[str, ...] = FINAL_SUBMIT_TEXTS) -> FillResult:
    generic = fill_application_form(page, profile, final_submit_texts)
    extra_filled = _ashby_fill_text(page, profile) + _ashby_location(page, profile)
    upload_count, cv, cover = _ashby_upload(page, profile)
    detected = page.locator('input, textarea, select, [role="combobox"]').count()
    submit = find_action_control(page, final_submit_texts, exact=True)
    unresolved = _required_unanswered(page, generic.required_unanswered)
    return FillResult(
        filled=generic.filled + extra_filled + upload_count,
        required_unanswered=unresolved,
        safe_submit_found=submit is not None,
        next_step_found=generic.next_step_found,
        action_audit=generic.action_audit,
        restricted_questions=generic.restricted_questions,
        fields_detected=max(generic.fields_detected, detected),
        required_fields=max(generic.required_fields, len(unresolved)),
        optional_skipped=generic.optional_skipped,
        cv_uploaded=generic.cv_uploaded or cv,
        cover_letter_uploaded=generic.cover_letter_uploaded or cover,
        field_audit=generic.field_audit,
    )

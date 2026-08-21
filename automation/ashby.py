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
    try:
        parts.append(locator.locator("xpath=ancestor::*[self::label or self::div][1]").inner_text(timeout=500))
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
            if "cover" in label and profile.cover_letter_path:
                control.set_input_files(profile.cover_letter_path)
                uploaded += 1
                cover = True
            else:
                control.set_input_files(profile.resume_path)
                uploaded += 1
                cv = True
        except Exception:
            continue
    return uploaded, cv, cover


def _ashby_fill_text(page: Any, profile: ApplicantProfile) -> int:
    values = {
        "first name": profile.first_name,
        "last name": profile.employer_last_name,
        "email": profile.email,
        "phone": profile.phone,
        "linkedin": profile.linkedin_url,
        "website": profile.website_url,
        "city": profile.city,
    }
    filled = 0
    controls = page.locator('input:not([type="hidden"]):not([type="file"]):not([type="checkbox"]):not([type="radio"]), textarea')
    for index in range(controls.count()):
        control = controls.nth(index)
        try:
            if not control.is_visible() or control.is_disabled() or control.input_value().strip():
                continue
            label = _text(control)
            for marker, value in values.items():
                if marker in label and value:
                    control.fill(str(value))
                    filled += 1
                    break
        except Exception:
            continue
    return filled


def fill_ashby_application(page: Any, profile: ApplicantProfile, final_submit_texts: tuple[str, ...] = FINAL_SUBMIT_TEXTS) -> FillResult:
    generic = fill_application_form(page, profile, final_submit_texts)
    extra_filled = _ashby_fill_text(page, profile)
    upload_count, cv, cover = _ashby_upload(page, profile)
    detected = page.locator('input, textarea, select, [role="combobox"]').count()
    submit = find_action_control(page, final_submit_texts, exact=True)
    return FillResult(
        filled=generic.filled + extra_filled + upload_count,
        required_unanswered=generic.required_unanswered,
        safe_submit_found=submit is not None,
        next_step_found=generic.next_step_found,
        action_audit=generic.action_audit,
        restricted_questions=generic.restricted_questions,
        fields_detected=max(generic.fields_detected, detected),
        required_fields=generic.required_fields,
        optional_skipped=generic.optional_skipped,
        cv_uploaded=generic.cv_uploaded or cv,
        cover_letter_uploaded=generic.cover_letter_uploaded or cover,
        field_audit=generic.field_audit,
    )

from dataclasses import dataclass
import logging
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from playwright.sync_api import Frame, Locator, Page
else:
    Frame = Locator = Page = Any

from automation.profile import ApplicantProfile
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


FIELD_ALIASES = {
    "first_name": (
        "first name", "firstname", "given name", "given-name",
    ),
    "middle_name": (
        "middle name", "middlename", "middle initial", "additional name",
    ),
    "last_name": (
        "last name", "lastname", "surname", "family name", "family-name",
    ),
    "full_name": (
        "full name", "your name", "candidate name",
    ),
    "email": (
        "email", "email address", "e-mail",
    ),
    "phone": (
        "phone", "phone number", "mobile", "telephone", "contact number",
    ),
    "city": (
        "city", "current city", "location city",
    ),
    "country": (
        "country", "current country", "country of residence",
    ),
    "address": (
        "address", "street address", "home address",
    ),
    "postal_code": (
        "postal code", "postcode", "zip code", "zip",
    ),
    "linkedin_url": (
        "linkedin", "linkedin profile", "linkedin url",
    ),
    "website_url": (
        "website", "portfolio", "personal website",
    ),
    "notice_period": (
        "notice period", "availability", "when can you start",
    ),
    "salary_expectation": (
        "salary expectation", "expected salary", "desired salary",
        "compensation expectation",
    ),
}

FINAL_SUBMIT_TEXTS = (
    "submit application",
    "send application",
    "complete application",
    "finish application",
    "confirm and submit",
    "submit",
)

NEXT_STEP_TEXTS = (
    "continue",
    "next",
    "save and continue",
    "proceed",
    "review application",
    "review and submit",
)

NEGATIVE_BUTTON_TEXTS = (
    "cancel",
    "back",
    "close",
    "delete",
    "withdraw",
    "save job",
)


def normalize(value: str | None) -> str:
    return " ".join((value or "").lower().split())


def profile_value(
    profile: ApplicantProfile,
    field: str,
    *,
    has_middle_name_field: bool,
) -> str:
    if field == "full_name":
        return profile.full_name
    if field == "last_name" and not has_middle_name_field:
        return profile.employer_last_name
    return str(getattr(profile, field, "") or "")


def identify_field(label: str) -> str | None:
    intent = identify_intent(label)
    mapping = {
        Intent.FIRST_NAME: "first_name", Intent.MIDDLE_NAME: "middle_name",
        Intent.LAST_NAME: "last_name", Intent.FULL_NAME: "full_name",
        Intent.EMAIL: "email", Intent.PHONE: "phone", Intent.CITY: "city",
        Intent.CURRENT_COUNTRY: "country", Intent.ADDRESS: "address",
        Intent.POSTAL_CODE: "postal_code", Intent.LINKEDIN: "linkedin_url",
        Intent.WEBSITE: "website_url", Intent.NOTICE_PERIOD: "notice_period",
        Intent.SALARY: "salary_expectation",
    }
    return mapping.get(intent)


def form_frames(page: Page) -> tuple[Frame, ...]:
    frames: list[Frame] = [page.main_frame]
    frames.extend(frame for frame in page.frames if frame != page.main_frame)
    unique: list[Frame] = []
    seen: set[int] = set()
    for frame in frames:
        marker = id(frame)
        if marker not in seen:
            seen.add(marker)
            unique.append(frame)
    return tuple(unique)


def _label_for(locator: Locator) -> str:
    locator_id = locator.get_attribute("id")
    if locator_id:
        label = locator.page.locator(f'label[for="{locator_id}"]')
        if label.count():
            try:
                return label.first.inner_text()
            except Exception:
                pass

    for attribute in (
        "aria-label",
        "placeholder",
        "name",
        "autocomplete",
        "data-qa",
        "data-testid",
        "id",
    ):
        value = locator.get_attribute(attribute)
        if value:
            return value

    try:
        parent_text = locator.locator("xpath=..").inner_text()
        if parent_text:
            return parent_text[:240]
    except Exception:
        pass
    return ""


def _has_middle_name_field(frame: Frame) -> bool:
    controls = frame.locator(
        'input:not([type="hidden"]):not([type="file"]):not([type="submit"]), textarea'
    )
    for index in range(controls.count()):
        try:
            if identify_field(_label_for(controls.nth(index))) == "middle_name":
                return True
        except Exception:
            continue
    return False


def _fill_text_inputs(frame: Frame, profile: ApplicantProfile) -> int:
    filled = 0
    has_middle = _has_middle_name_field(frame)
    controls = frame.locator(
        'input:not([type="hidden"]):not([type="file"]):not([type="submit"])'
        ':not([type="button"]):not([type="checkbox"]):not([type="radio"]), textarea'
    )
    for index in range(controls.count()):
        control = controls.nth(index)
        try:
            if not control.is_visible() or control.is_disabled():
                continue
            field = identify_field(_label_for(control))
            if not field:
                continue
            value = profile_value(
                profile,
                field,
                has_middle_name_field=has_middle,
            )
            if not value:
                continue
            current = control.input_value()
            if current.strip():
                continue
            control.fill(value)
            filled += 1
        except Exception:
            continue
    return filled


def _upload_documents(frame: Frame, profile: ApplicantProfile) -> int:
    uploaded = 0
    files = frame.locator('input[type="file"]')
    for index in range(files.count()):
        control = files.nth(index)
        label = normalize(_label_for(control))
        try:
            if any(term in label for term in ("cover", "letter")):
                if profile.cover_letter_path:
                    control.set_input_files(profile.cover_letter_path)
                    uploaded += 1
            elif any(
                term in label
                for term in (
                    "certificate",
                    "supporting",
                    "additional document",
                    "other document",
                )
            ):
                if profile.supporting_document_path:
                    control.set_input_files(profile.supporting_document_path)
                    uploaded += 1
            else:
                control.set_input_files(profile.resume_path)
                uploaded += 1
        except Exception:
            continue
    return uploaded


def _select_by_visible_text(select: Locator, preferred: str) -> bool:
    attempts = (preferred, preferred.lower(), preferred.upper())
    for label in attempts:
        try:
            select.select_option(label=label)
            return True
        except Exception:
            continue

    options = select.locator("option")
    for index in range(options.count()):
        option = options.nth(index)
        try:
            text = normalize(option.inner_text())
            if normalize(preferred) in text or text in normalize(preferred):
                value = option.get_attribute("value")
                if value is not None:
                    select.select_option(value=value)
                    return True
        except Exception:
            continue
    return False


def _select_common_options(frame: Frame, profile: ApplicantProfile) -> int:
    filled = 0
    selects = frame.locator("select")
    for index in range(selects.count()):
        select = selects.nth(index)
        try:
            if not select.is_visible() or select.is_disabled():
                continue
            label = normalize(_label_for(select))
            success = False
            if "country" in label:
                success = _select_by_visible_text(select, profile.country)
            elif "sponsor" in label or "visa" in label:
                answer = "Yes" if profile.requires_sponsorship else "No"
                success = _select_by_visible_text(select, answer)
            elif "work authorization" in label or "authorisation" in label:
                success = _select_by_visible_text(
                    select,
                    profile.work_authorization,
                )
            if success:
                filled += 1
        except Exception:
            continue
    return filled


def _required_unanswered(frame: Frame) -> list[str]:
    unanswered: list[str] = []
    controls = frame.locator(
        'input[required]:not([type="hidden"]), textarea[required], select[required], '
        'input[aria-required="true"]:not([type="hidden"]), '
        'textarea[aria-required="true"], select[aria-required="true"]'
    )
    for index in range(controls.count()):
        control = controls.nth(index)
        try:
            if not control.is_visible() or control.is_disabled():
                continue
            tag = control.evaluate("(node) => node.tagName.toLowerCase()")
            control_type = normalize(control.get_attribute("type"))
            answered = True
            if tag == "select":
                answered = bool(control.input_value())
            elif control_type in {"checkbox", "radio"}:
                name = control.get_attribute("name")
                if name:
                    answered = (
                        frame.locator(f'input[name="{name}"]:checked').count() > 0
                    )
                else:
                    answered = control.is_checked()
            elif control_type == "file":
                answered = bool(control.input_value())
            else:
                answered = bool(control.input_value().strip())

            if not answered:
                label = (
                    _label_for(control)
                    or control.get_attribute("name")
                    or "Unknown field"
                )
                unanswered.append(" ".join(label.split())[:180])
        except Exception:
            continue
    return unanswered


def _control_text(control: Locator) -> str:
    for attribute in ("value", "aria-label", "title", "name", "data-testid"):
        value = control.get_attribute(attribute)
        if value:
            return normalize(value)
    try:
        return normalize(control.inner_text())
    except Exception:
        return ""


def _candidate_controls(frame: Frame) -> Locator:
    return frame.locator(
        'button, input[type="submit"], input[type="button"], '
        'a[role="button"], div[role="button"]'
    )


def audit_action_controls(page: Page, texts: tuple[str, ...], *, exact: bool = False) -> tuple[str, ...]:
    entries: list[str] = []
    for frame_index, frame in enumerate(form_frames(page)):
        controls = _candidate_controls(frame)
        for index in range(controls.count()):
            control = controls.nth(index)
            try:
                text = _control_text(control)
                visible = control.is_visible()
                enabled = control.is_enabled()
                negative = bool(text and any(term in text for term in NEGATIVE_BUTTON_TEXTS))
                matched = bool(text) and (
                    any(text == term for term in texts)
                    if exact
                    else any(text == term or term in text for term in texts)
                )
                entries.append(
                    f"frame={frame_index} index={index} text={text!r} "
                    f"visible={visible} enabled={enabled} negative={negative} matched={matched}"
                )
            except Exception as exc:
                entries.append(
                    f"frame={frame_index} index={index} inspection_error={type(exc).__name__}: {exc}"
                )
    if not entries:
        entries.append("no candidate action controls found")
    logger.info(
        "Action-control audit | exact=%s | expected=%s | candidates=%s",
        exact,
        texts,
        " || ".join(entries),
    )
    return tuple(entries)


def find_action_control(
    page: Page,
    texts: tuple[str, ...],
    *,
    exact: bool = False,
) -> tuple[Frame, Locator] | None:
    for frame_index, frame in enumerate(form_frames(page)):
        controls = _candidate_controls(frame)
        for index in range(controls.count()):
            control = controls.nth(index)
            try:
                if not control.is_visible() or not control.is_enabled():
                    continue
                text = _control_text(control)
                if not text or any(term in text for term in NEGATIVE_BUTTON_TEXTS):
                    continue
                matched = (
                    any(text == term for term in texts)
                    if exact
                    else any(text == term or term in text for term in texts)
                )
                if matched:
                    logger.info(
                        "Action control accepted | frame=%s | index=%s | text=%r | expected=%s | exact=%s",
                        frame_index, index, text, texts, exact,
                    )
                    return frame, control
            except Exception as exc:
                logger.debug(
                    "Action control inspection failed | frame=%s | index=%s | error=%s: %s",
                    frame_index, index, type(exc).__name__, exc,
                )
    audit_action_controls(page, texts, exact=exact)
    return None


def click_safe_submit(
    page: Page,
    texts: tuple[str, ...] = FINAL_SUBMIT_TEXTS,
) -> bool:
    result = find_action_control(page, texts, exact=True)
    if not result:
        return False
    _, control = result
    control.scroll_into_view_if_needed()
    control.click()
    return True


def click_next_step(page: Page) -> bool:
    result = find_action_control(page, NEXT_STEP_TEXTS)
    if not result:
        return False
    _, control = result
    control.scroll_into_view_if_needed()
    control.click()
    return True



def _is_required(control: Locator) -> bool:
    return bool(control.get_attribute("required") is not None or normalize(control.get_attribute("aria-required")) == "true")


def _choose_radio_or_checkbox(frame: Frame, profile: ApplicantProfile) -> tuple[int, list[FieldAudit], list[str]]:
    filled = 0
    audits: list[FieldAudit] = []
    restricted: list[str] = []
    groups: set[str] = set()
    controls = frame.locator('input[type="radio"], input[type="checkbox"]')
    for index in range(controls.count()):
        control = controls.nth(index)
        try:
            if not control.is_visible() or control.is_disabled() or control.is_checked():
                continue
            name = control.get_attribute("name") or f"__single_{index}"
            if name in groups:
                continue
            groups.add(name)
            label = _label_for(control)
            group = frame.locator(f'input[name="{name}"]') if not name.startswith('__single_') else control
            combined = label
            if group.count() > 1:
                try:
                    combined = group.first.locator("xpath=../..").inner_text()[:500]
                except Exception:
                    pass
            restriction = restriction_reason(combined)
            if restriction:
                restricted.append(combined.strip()[:220])
                audits.append(FieldAudit(combined[:180], identify_intent(combined).value, _is_required(control), "blocked", restriction))
                continue
            resolution = resolve_question(combined, profile)
            if not resolution.auto_fill_allowed:
                continue
            target = None
            for option_index in range(group.count()):
                option = group.nth(option_index)
                option_text = normalize(_label_for(option) + " " + (option.get_attribute("value") or ""))
                if normalize(resolution.value) == option_text or normalize(resolution.value) in option_text:
                    target = option
                    break
            if target is None and group.count() == 1 and resolution.value.lower() in {"yes", "true", "agree"}:
                target = group.first
            if target is not None:
                target.check()
                filled += 1
                audits.append(FieldAudit(combined[:180], resolution.intent.value, _is_required(control), "selected", "success"))
        except Exception:
            continue
    return filled, audits, restricted


def _fill_semantic_text(frame: Frame, profile: ApplicantProfile) -> tuple[int, list[FieldAudit], list[str], int, int]:
    filled = 0
    audits: list[FieldAudit] = []
    restricted: list[str] = []
    detected = required_count = 0
    has_middle = _has_middle_name_field(frame)
    controls = frame.locator('input:not([type="hidden"]):not([type="file"]):not([type="submit"]):not([type="button"]):not([type="checkbox"]):not([type="radio"]), textarea')
    for index in range(controls.count()):
        control = controls.nth(index)
        try:
            if not control.is_visible() or control.is_disabled():
                continue
            detected += 1
            required = _is_required(control)
            required_count += int(required)
            label = _label_for(control)
            restriction = restriction_reason(label)
            if restriction:
                restricted.append(label.strip()[:220])
                audits.append(FieldAudit(label[:180], identify_intent(label).value, required, "blocked", restriction))
                continue
            if control.input_value().strip():
                continue
            resolution = resolve_question(label, profile, has_middle_name_field=has_middle)
            if resolution.auto_fill_allowed and resolution.value:
                control.scroll_into_view_if_needed()
                control.fill(resolution.value)
                filled += 1
                audits.append(FieldAudit(label[:180], resolution.intent.value, required, "filled", "success"))
            elif required:
                audits.append(FieldAudit(label[:180], resolution.intent.value, True, "manual", resolution.reason))
        except Exception:
            continue
    return filled, audits, restricted, detected, required_count


def _select_semantic(frame: Frame, profile: ApplicantProfile) -> tuple[int, list[FieldAudit], int, int]:
    filled = 0
    audits: list[FieldAudit] = []
    detected = required_count = 0
    selects = frame.locator("select")
    for index in range(selects.count()):
        select = selects.nth(index)
        try:
            if not select.is_visible() or select.is_disabled():
                continue
            detected += 1
            required = _is_required(select)
            required_count += int(required)
            if select.input_value().strip():
                continue
            label = _label_for(select)
            resolution = resolve_question(label, profile)
            if resolution.auto_fill_allowed and _select_by_visible_text(select, resolution.value):
                filled += 1
                audits.append(FieldAudit(label[:180], resolution.intent.value, required, "selected", "success"))
            elif required:
                audits.append(FieldAudit(label[:180], resolution.intent.value, True, "manual", resolution.reason))
        except Exception:
            continue
    return filled, audits, detected, required_count


def _fill_custom_comboboxes(frame: Frame, profile: ApplicantProfile) -> tuple[int, list[FieldAudit], int, int]:
    filled = 0
    audits: list[FieldAudit] = []
    detected = required_count = 0
    boxes = frame.locator('[role="combobox"]:not(select)')
    for index in range(boxes.count()):
        box = boxes.nth(index)
        try:
            if not box.is_visible() or box.is_disabled():
                continue
            detected += 1
            required = _is_required(box)
            required_count += int(required)
            label = _label_for(box)
            resolution = resolve_question(label, profile)
            if not resolution.auto_fill_allowed:
                continue
            box.scroll_into_view_if_needed()
            box.click()
            try:
                box.fill(resolution.value)
            except Exception:
                pass
            frame.page.wait_for_timeout(350)
            options = frame.locator('[role="option"]:visible')
            chosen = None
            for option_index in range(options.count()):
                option = options.nth(option_index)
                text = normalize(option.inner_text())
                if normalize(resolution.value) == text or normalize(resolution.value) in text or text in normalize(resolution.value):
                    chosen = option
                    break
            if chosen is not None:
                chosen.click()
                filled += 1
                audits.append(FieldAudit(label[:180], resolution.intent.value, required, "selected", "success"))
        except Exception:
            continue
    return filled, audits, detected, required_count

def fill_application_form(
    page: Page,
    profile: ApplicantProfile,
    final_submit_texts: tuple[str, ...] = FINAL_SUBMIT_TEXTS,
) -> FillResult:
    filled = 0
    unanswered: list[str] = []
    restricted: list[str] = []
    audits: list[FieldAudit] = []
    detected = required_count = optional_skipped = 0
    cv_uploaded = cover_uploaded = False

    for frame in form_frames(page):
        count, entries, blocked, found, required = _fill_semantic_text(frame, profile)
        filled += count; audits.extend(entries); restricted.extend(blocked)
        detected += found; required_count += required

        count, entries, found, required = _select_semantic(frame, profile)
        filled += count; audits.extend(entries); detected += found; required_count += required

        count, entries, found, required = _fill_custom_comboboxes(frame, profile)
        filled += count; audits.extend(entries); detected += found; required_count += required

        count, entries, blocked = _choose_radio_or_checkbox(frame, profile)
        filled += count; audits.extend(entries); restricted.extend(blocked)

        files = frame.locator('input[type="file"]')
        detected += files.count()
        for index in range(files.count()):
            control = files.nth(index)
            try:
                if not control.is_visible() and control.get_attribute("type") != "file":
                    continue
                label = normalize(_label_for(control))
                if control.input_value():
                    continue
                if any(term in label for term in ("cover", "letter")) and profile.cover_letter_path:
                    control.set_input_files(profile.cover_letter_path); filled += 1; cover_uploaded = True
                elif any(term in label for term in ("certificate", "supporting", "additional document", "other document")) and profile.supporting_document_path:
                    control.set_input_files(profile.supporting_document_path); filled += 1
                else:
                    control.set_input_files(profile.resume_path); filled += 1; cv_uploaded = True
            except Exception:
                continue
        unanswered.extend(_required_unanswered(frame))

    optional_skipped = sum(1 for audit in audits if not audit.required and audit.action in {"manual", "blocked"})
    submit_control = find_action_control(page, final_submit_texts, exact=True)
    next_control = find_action_control(page, NEXT_STEP_TEXTS)
    audit_controls = () if submit_control is not None else audit_action_controls(page, final_submit_texts, exact=True)
    return FillResult(
        filled=filled,
        required_unanswered=tuple(dict.fromkeys(unanswered)),
        safe_submit_found=submit_control is not None,
        next_step_found=next_control is not None,
        action_audit=audit_controls,
        restricted_questions=tuple(dict.fromkeys(restricted)),
        fields_detected=detected,
        required_fields=required_count,
        optional_skipped=optional_skipped,
        cv_uploaded=cv_uploaded,
        cover_letter_uploaded=cover_uploaded,
        field_audit=tuple(audits),
    )

from __future__ import annotations

import argparse
import hashlib
import json
import platform
import subprocess
import sys
import traceback
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse

from playwright.sync_api import sync_playwright

from agents.scorer import Scorer
from automation.application_pipeline import profile_for_package
from automation.ashby import fill_ashby_application
from automation.ats import adapter_for_url
from automation.forms import fill_application_form
from automation.live_test_target import PERMITFLOW_ADMINISTRATIVE_ASSISTANT, canonical_url
from automation.package_builder import build_application_package
from automation.profile import CANONICAL_PROFILE_FILE, load_profile
from automation.tailoring import tailor_documents
from config.settings import APPLICANT_PROFILE_FILE, AUTOMATION_SCREENSHOT_DIR, BROWSER_PROFILE_DIR
from core.models import Job


def _safe_name(url: str) -> str:
    host = urlparse(url).netloc.lower().replace("www.", "")
    return "".join(ch if ch.isalnum() else "_" for ch in host).strip("_") or "application"


def _wait_for_application_controls(page) -> None:
    page.wait_for_load_state("domcontentloaded")
    try:
        page.wait_for_load_state("networkidle", timeout=15000)
    except Exception:
        pass
    page.locator('input, textarea, select, [role="combobox"]').first.wait_for(state="attached", timeout=30000)
    page.wait_for_timeout(1000)


def _job_from_live_page(page, requested_url: str) -> Job:
    body = ""
    try:
        body = page.locator("body").inner_text(timeout=5000)
    except Exception:
        pass

    if canonical_url(requested_url) == canonical_url(PERMITFLOW_ADMINISTRATIVE_ASSISTANT.application_url):
        company = PERMITFLOW_ADMINISTRATIVE_ASSISTANT.employer
        title = PERMITFLOW_ADMINISTRATIVE_ASSISTANT.title
    else:
        company = urlparse(page.url).netloc.replace("www.", "")
        try:
            title = page.locator("h1").first.inner_text(timeout=2000).strip()
        except Exception:
            title = page.title().strip() or "Application"

    return Job(
        company=company,
        title=title,
        location="Remote",
        source=adapter_for_url(page.url).name,
        url=page.url,
        description=body,
    )


def _rehearsal_job_id(url: str) -> int:
    return int(hashlib.sha256(url.encode("utf-8")).hexdigest()[:8], 16)


def _prepare_tailored_profile(job: Job, job_id: int, base_profile):
    decision = Scorer().evaluate(job)
    documents = tailor_documents(job, job_id, base_profile)
    package = build_application_package(job, documents, decision)
    browser_profile = profile_for_package(base_profile, package)
    return decision, documents, package, browser_profile


def _git_value(*args: str) -> str:
    try:
        return subprocess.check_output(["git", *args], text=True, stderr=subprocess.DEVNULL, timeout=3).strip()
    except Exception:
        return "unknown"


def _profile_snapshot(profile) -> dict:
    education = getattr(profile, "highest_education", None)
    employment = getattr(profile, "employment_history", ()) or ()
    return {
        "runtime_profile_file": str(APPLICANT_PROFILE_FILE),
        "runtime_profile_exists": APPLICANT_PROFILE_FILE.is_file(),
        "canonical_profile_file": str(CANONICAL_PROFILE_FILE),
        "canonical_profile_exists": CANONICAL_PROFILE_FILE.is_file(),
        "name": profile.full_name,
        "email": profile.email,
        "phone": profile.phone,
        "city": profile.city,
        "country": profile.country,
        "postal_code": profile.postal_code,
        "linkedin_url": profile.linkedin_url,
        "notice_period": profile.notice_period,
        "salary_expectation": profile.salary_expectation,
        "auto_fill_demographics": profile.auto_fill_demographics,
        "demographics": dict(profile.demographics),
        "source_resume_path": profile.source_resume_path,
        "source_resume_exists": bool(profile.source_resume_path and Path(profile.source_resume_path).is_file()),
        "resume_path_before_tailoring": profile.resume_path,
        "education": asdict(education) if education is not None else None,
        "employment_records": len(employment),
    }


def _runtime_snapshot() -> dict:
    return {
        "python": sys.version,
        "python_executable": sys.executable,
        "platform": platform.platform(),
        "working_directory": str(Path.cwd()),
        "git_branch": _git_value("branch", "--show-current"),
        "git_commit": _git_value("rev-parse", "HEAD"),
        "git_status": _git_value("status", "--short"),
        "browser_profile_dir": str(BROWSER_PROFILE_DIR),
    }


def _write_bundle(report_path: Path, text_path: Path, payload: dict) -> None:
    payload["generated_at"] = datetime.now(timezone.utc).isoformat()
    report_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    lines = [
        "VOCANTA AUTOFILL DIAGNOSTICS",
        f"Status: {payload.get('status', 'unknown')}",
        f"Requested URL: {payload.get('requested_url', '')}",
        f"Final URL: {payload.get('final_url', '')}",
        f"ATS: {payload.get('ats', '')}",
        f"Job: {payload.get('company', '')} | {payload.get('title', '')}",
        f"Git: {payload.get('runtime', {}).get('git_branch', '')} | {payload.get('runtime', {}).get('git_commit', '')}",
        f"Runtime profile: {payload.get('profile', {}).get('runtime_profile_file', '')}",
        f"Tailored CV: {payload.get('uploaded_resume_pdf', '')}",
        f"Tailored cover letter: {payload.get('uploaded_cover_letter_pdf', '')}",
        f"Fields detected: {payload.get('fields_detected', 0)}",
        f"Fields filled: {payload.get('fields_filled', 0)}",
        f"CV uploaded: {payload.get('cv_uploaded', False)}",
        f"Cover letter uploaded: {payload.get('cover_letter_uploaded', False)}",
        f"Required unanswered: {payload.get('required_unanswered', [])}",
        f"Browser console errors: {payload.get('browser_console_errors', [])}",
        f"Page errors: {payload.get('page_errors', [])}",
        f"Failed requests: {payload.get('failed_requests', [])}",
        f"Exception: {payload.get('exception', '')}",
        f"Screenshot: {payload.get('screenshot', '')}",
        f"JSON report: {report_path}",
    ]
    text_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Populate a real job application from the VOCANTA profile without submitting it.")
    parser.add_argument("url", help="Direct application URL on a supported ATS")
    parser.add_argument("--headless", action="store_true", help="Run without showing the browser")
    args = parser.parse_args()

    AUTOMATION_SCREENSHOT_DIR.mkdir(parents=True, exist_ok=True)
    BROWSER_PROFILE_DIR.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    prefix = f"autofill_{_safe_name(args.url)}_{stamp}"
    screenshot_path = AUTOMATION_SCREENSHOT_DIR / f"{prefix}.png"
    report_path = AUTOMATION_SCREENSHOT_DIR / f"{prefix}.json"
    text_path = AUTOMATION_SCREENSHOT_DIR / f"{prefix}.txt"

    payload: dict = {
        "status": "STARTED",
        "requested_url": args.url,
        "final_url": "",
        "runtime": _runtime_snapshot(),
        "browser_console_errors": [],
        "page_errors": [],
        "failed_requests": [],
        "submitted": False,
        "screenshot": str(screenshot_path),
    }

    try:
        base_profile = load_profile()
        payload["profile"] = _profile_snapshot(base_profile)

        with sync_playwright() as playwright:
            context = playwright.chromium.launch_persistent_context(
                user_data_dir=str(BROWSER_PROFILE_DIR),
                headless=args.headless,
                viewport={"width": 1440, "height": 1000},
            )
            page = context.pages[0] if context.pages else context.new_page()
            page.on("console", lambda message: payload["browser_console_errors"].append(message.text) if message.type == "error" else None)
            page.on("pageerror", lambda error: payload["page_errors"].append(str(error)))
            page.on("requestfailed", lambda request: payload["failed_requests"].append(f"{request.method} {request.url} | {request.failure}"))
            try:
                page.goto(args.url, wait_until="domcontentloaded", timeout=60000)
                payload["final_url"] = page.url
                _wait_for_application_controls(page)

                adapter = adapter_for_url(page.url)
                payload["ats"] = adapter.name
                job = _job_from_live_page(page, args.url)
                payload["company"] = job.company
                payload["title"] = job.title
                decision, documents, package, profile = _prepare_tailored_profile(job, _rehearsal_job_id(args.url), base_profile)
                payload.update({
                    "tailoring_category": documents.category,
                    "tailored_resume_docx": str(documents.resume_path),
                    "tailored_cover_letter_docx": str(documents.cover_letter_path),
                    "uploaded_resume_pdf": str(package.cv_pdf),
                    "uploaded_cover_letter_pdf": str(package.cover_letter_pdf),
                    "resume_is_tailored_package": str(profile.resume_path) == str(package.cv_pdf),
                    "application_score": decision.score,
                })
                job_context = f"{job.title}\n{job.description}"

                result = (
                    fill_ashby_application(page, profile, adapter.final_submit_texts, job_context=job_context)
                    if adapter.name == "ASHBY"
                    else fill_application_form(page, profile, adapter.final_submit_texts, job_context=job_context)
                )
                page.wait_for_timeout(750)
                page.screenshot(path=str(screenshot_path), full_page=True)
                payload.update({
                    "status": "COMPLETE",
                    "final_url": page.url,
                    "fields_detected": result.fields_detected,
                    "fields_filled": result.filled,
                    "required_fields": result.required_fields,
                    "optional_skipped": result.optional_skipped,
                    "cv_uploaded": result.cv_uploaded,
                    "cover_letter_uploaded": result.cover_letter_uploaded,
                    "required_unanswered": list(result.required_unanswered),
                    "restricted_questions": list(result.restricted_questions),
                    "action_audit": list(result.action_audit),
                    "field_audit": [asdict(item) for item in result.field_audit],
                    "final_submit_detected": result.safe_submit_found,
                })
                _write_bundle(report_path, text_path, payload)

                print("VOCANTA AUTOFILL REHEARSAL: COMPLETE")
                print(f"ATS: {adapter.name}")
                print(f"Job: {job.company} | {job.title}")
                print(f"Employer upload CV: {package.cv_pdf}")
                print(f"Fields detected: {result.fields_detected}")
                print(f"Fields filled: {result.filled}")
                print(f"Required unanswered: {len(result.required_unanswered)}")
                print(f"DIAGNOSTIC JSON: {report_path}")
                print(f"DIAGNOSTIC TEXT: {text_path}")
                print(f"SCREENSHOT: {screenshot_path}")
                print("SUBMISSION: DISABLED. Final submit was not clicked.")
                if not args.headless:
                    input("Review the populated application. Press Enter to close the browser...")
                return 0
            finally:
                context.close()
    except Exception as exc:
        payload["status"] = "FAILED"
        payload["exception"] = f"{type(exc).__name__}: {exc}"
        payload["traceback"] = traceback.format_exc()
        try:
            if "page" in locals() and not page.is_closed():
                payload["final_url"] = page.url
                page.screenshot(path=str(screenshot_path), full_page=True)
        except Exception as screenshot_exc:
            payload["screenshot_error"] = str(screenshot_exc)
        _write_bundle(report_path, text_path, payload)
        print("VOCANTA AUTOFILL REHEARSAL: FAILED")
        print(payload["exception"])
        print(f"DIAGNOSTIC JSON: {report_path}")
        print(f"DIAGNOSTIC TEXT: {text_path}")
        print(f"SCREENSHOT: {screenshot_path}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())

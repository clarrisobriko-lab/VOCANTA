from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from urllib.parse import urlparse

from playwright.sync_api import sync_playwright

from agents.scorer import Scorer
from automation.application_pipeline import profile_for_package
from automation.ashby import fill_ashby_application
from automation.ats import adapter_for_url
from automation.forms import fill_application_form
from automation.live_test_target import PERMITFLOW_ADMINISTRATIVE_ASSISTANT, canonical_url
from automation.package_builder import build_application_package
from automation.profile import load_profile
from automation.tailoring import tailor_documents
from config.settings import AUTOMATION_SCREENSHOT_DIR, BROWSER_PROFILE_DIR
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


def main() -> int:
    parser = argparse.ArgumentParser(description="Populate a real job application from the VOCANTA profile without submitting it.")
    parser.add_argument("url", help="Direct application URL on a supported ATS")
    parser.add_argument("--headless", action="store_true", help="Run without showing the browser")
    args = parser.parse_args()

    base_profile = load_profile()
    AUTOMATION_SCREENSHOT_DIR.mkdir(parents=True, exist_ok=True)
    BROWSER_PROFILE_DIR.mkdir(parents=True, exist_ok=True)

    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    prefix = f"autofill_{_safe_name(args.url)}_{stamp}"
    screenshot_path = AUTOMATION_SCREENSHOT_DIR / f"{prefix}.png"
    report_path = AUTOMATION_SCREENSHOT_DIR / f"{prefix}.json"

    with sync_playwright() as playwright:
        context = playwright.chromium.launch_persistent_context(
            user_data_dir=str(BROWSER_PROFILE_DIR),
            headless=args.headless,
            viewport={"width": 1440, "height": 1000},
        )
        page = context.pages[0] if context.pages else context.new_page()
        try:
            page.goto(args.url, wait_until="domcontentloaded", timeout=60000)
            _wait_for_application_controls(page)

            adapter = adapter_for_url(page.url)
            job = _job_from_live_page(page, args.url)
            decision, documents, package, profile = _prepare_tailored_profile(
                job,
                _rehearsal_job_id(args.url),
                base_profile,
            )
            job_context = f"{job.title}\n{job.description}"

            result = (
                fill_ashby_application(page, profile, adapter.final_submit_texts, job_context=job_context)
                if adapter.name == "ASHBY"
                else fill_application_form(page, profile, adapter.final_submit_texts, job_context=job_context)
            )
            page.wait_for_timeout(750)
            page.screenshot(path=str(screenshot_path), full_page=True)

            report = {
                "requested_url": args.url,
                "final_url": page.url,
                "ats": adapter.name,
                "company": job.company,
                "title": job.title,
                "tailoring_category": documents.category,
                "tailored_resume_docx": str(documents.resume_path),
                "tailored_cover_letter_docx": str(documents.cover_letter_path),
                "uploaded_resume_pdf": str(package.cv_pdf),
                "uploaded_cover_letter_pdf": str(package.cover_letter_pdf),
                "resume_is_tailored_package": str(profile.resume_path) == str(package.cv_pdf),
                "application_score": decision.score,
                "fields_detected": result.fields_detected,
                "fields_filled": result.filled,
                "cv_uploaded": result.cv_uploaded,
                "cover_letter_uploaded": result.cover_letter_uploaded,
                "required_unanswered": list(result.required_unanswered),
                "restricted_questions": list(result.restricted_questions),
                "final_submit_detected": result.safe_submit_found,
                "submitted": False,
                "screenshot": str(screenshot_path),
            }
            report_path.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")

            print("VOCANTA AUTOFILL REHEARSAL: COMPLETE")
            print(f"ATS: {adapter.name}")
            print(f"Job: {job.company} | {job.title}")
            print(f"Tailored CV source: {documents.resume_path}")
            print(f"Employer upload CV: {package.cv_pdf}")
            print(f"Employer upload cover letter: {package.cover_letter_pdf}")
            print(f"Fields detected: {result.fields_detected}")
            print(f"Fields filled: {result.filled}")
            print(f"CV uploaded: {result.cv_uploaded}")
            print(f"Required unanswered: {len(result.required_unanswered)}")
            print(f"Screenshot: {screenshot_path}")
            print(f"Report: {report_path}")
            print("SUBMISSION: DISABLED. Final submit was not clicked.")
            if not args.headless:
                input("Review the populated application. Press Enter to close the browser...")
            return 0
        finally:
            context.close()


if __name__ == "__main__":
    raise SystemExit(main())

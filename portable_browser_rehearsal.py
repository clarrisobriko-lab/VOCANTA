from __future__ import annotations

import argparse

from playwright.sync_api import sync_playwright

from agents.scorer import Scorer
from automation.application_pipeline import profile_for_package, validate_browser_documents
from automation.ashby import fill_ashby_application
from automation.ats import adapter_for_url
from automation.forms import fill_application_form
from automation.package_builder import build_application_package
from automation.profile import load_profile
from automation.tailoring import tailor_documents
from config.settings import AUTOMATION_SCREENSHOT_DIR, BROWSER_PROFILE_DIR
from core.database import Database
from core.models import Job


def _wait_for_application_controls(page) -> None:
    page.wait_for_load_state("domcontentloaded")
    try:
        page.wait_for_load_state("networkidle", timeout=15000)
    except Exception:
        pass
    page.locator('input, textarea, select, [role="combobox"]').first.wait_for(state="attached", timeout=30000)
    page.wait_for_timeout(1500)


def _job_context(job: Job) -> str:
    return "\n".join(part for part in (job.title, job.description, job.location, job.employment_type) if part)


def main() -> int:
    parser = argparse.ArgumentParser(description="Controlled cross ATS browser rehearsal. Never submits.")
    parser.add_argument("job_id", type=int, help="VOCANTA database job id to rehearse")
    args = parser.parse_args()

    database = Database()
    try:
        row = database.connection.execute("SELECT * FROM jobs WHERE id = ?", (args.job_id,)).fetchone()
        if row is None:
            raise RuntimeError(f"Rehearsal blocked: job id {args.job_id} is not in the VOCANTA database")
        job = Job(company=row["company"], title=row["title"], location=row["location"], source=row["source"], url=row["url"], description=row["description"] or "", salary=row["salary"] or "", employment_type=row["employment_type"] or "", score=int(row["score"] or 0))
        decision = Scorer().evaluate(job)
        if not decision.should_apply:
            raise RuntimeError(f"Rehearsal blocked by scoring: {decision.reason}")
        adapter = adapter_for_url(job.url)
        if adapter.name.upper() == "UNKNOWN":
            raise RuntimeError("Rehearsal blocked: ATS is not recognised")

        profile = load_profile()
        documents = tailor_documents(job, int(row["id"]), profile)
        package = build_application_package(job, documents, decision)
        browser_profile = profile_for_package(profile, package)
        validate_browser_documents(browser_profile)
        vacancy_context = _job_context(job)
        AUTOMATION_SCREENSHOT_DIR.mkdir(parents=True, exist_ok=True)
        BROWSER_PROFILE_DIR.mkdir(parents=True, exist_ok=True)
        screenshot = AUTOMATION_SCREENSHOT_DIR / f"portable_rehearsal_{row['id']}_{adapter.name.lower()}.png"

        with sync_playwright() as playwright:
            context = playwright.chromium.launch_persistent_context(user_data_dir=str(BROWSER_PROFILE_DIR), headless=False, viewport={"width": 1440, "height": 1000})
            page = context.pages[0] if context.pages else context.new_page()
            try:
                page.goto(job.url, wait_until="domcontentloaded", timeout=60000)
                _wait_for_application_controls(page)
                live_adapter = adapter_for_url(page.url)
                if live_adapter.name != adapter.name:
                    raise RuntimeError(f"Rehearsal blocked: ATS changed from {adapter.name} to {live_adapter.name}")
                if live_adapter.name == "ASHBY":
                    result = fill_ashby_application(page, browser_profile, live_adapter.final_submit_texts)
                else:
                    result = fill_application_form(page, browser_profile, live_adapter.final_submit_texts, job_context=vacancy_context)
                page.wait_for_timeout(1000)
                page.screenshot(path=str(screenshot), full_page=True)
                print("PORTABLE CONTROLLED BROWSER REHEARSAL: COMPLETE")
                print(f"Target: {job.company} | {job.title}")
                print(f"ATS: {live_adapter.name}")
                print(f"Fields detected: {result.fields_detected}")
                print(f"Fields filled: {result.filled}")
                print(f"CV uploaded: {result.cv_uploaded}")
                print(f"Cover letter uploaded: {result.cover_letter_uploaded}")
                print(f"Required unanswered: {len(result.required_unanswered)}")
                for field in result.required_unanswered:
                    print(f"  REQUIRED: {field}")
                print(f"Restricted questions: {len(result.restricted_questions)}")
                for question in result.restricted_questions:
                    print(f"  RESTRICTED: {question}")
                print(f"Final submit detected: {result.safe_submit_found}")
                print(f"Screenshot: {screenshot}")
                print("SUBMISSION: DISABLED. Final submit was not clicked.")
                input("Review the populated browser form. Press Enter to close the rehearsal browser...")
                return 0
            finally:
                context.close()
    finally:
        database.close()


if __name__ == "__main__":
    raise SystemExit(main())

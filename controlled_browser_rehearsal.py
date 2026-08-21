from __future__ import annotations

from playwright.sync_api import sync_playwright

from agents.scorer import Scorer
from automation.application_pipeline import profile_for_package, validate_browser_documents
from automation.ats import adapter_for_url
from automation.forms import fill_application_form
from automation.live_test_target import PERMITFLOW_ADMINISTRATIVE_ASSISTANT, authorize_target, canonical_url
from automation.package_builder import build_application_package
from automation.profile import load_profile
from automation.tailoring import tailor_documents
from config.settings import AUTOMATION_SCREENSHOT_DIR, BROWSER_PROFILE_DIR
from core.database import Database
from core.models import Job


def main() -> int:
    target = PERMITFLOW_ADMINISTRATIVE_ASSISTANT
    authorize_target(target.application_url)
    database = Database()
    try:
        target_url = canonical_url(target.application_url)
        rows = database.connection.execute("SELECT * FROM jobs ORDER BY id DESC").fetchall()
        row = next((r for r in rows if canonical_url(r["url"]) == target_url), None)
        if row is None:
            raise RuntimeError("Browser rehearsal blocked: controlled target is not in the VOCANTA database. Run controlled_live_intake.py first.")
        job = Job(company=row["company"], title=row["title"], location=row["location"], source=row["source"], url=target.application_url, description=row["description"] or "", salary=row["salary"] or "", employment_type=row["employment_type"] or "", score=int(row["score"] or 0))
        decision = Scorer().evaluate(job)
        if not decision.should_apply:
            raise RuntimeError(f"Browser rehearsal blocked by scoring: {decision.reason}")
        profile = load_profile()
        documents = tailor_documents(job, int(row["id"]), profile)
        package = build_application_package(job, documents, decision)
        browser_profile = profile_for_package(profile, package)
        validate_browser_documents(browser_profile)
        AUTOMATION_SCREENSHOT_DIR.mkdir(parents=True, exist_ok=True)
        BROWSER_PROFILE_DIR.mkdir(parents=True, exist_ok=True)
        screenshot = AUTOMATION_SCREENSHOT_DIR / f"controlled_rehearsal_{row['id']}.png"
        with sync_playwright() as playwright:
            context = playwright.chromium.launch_persistent_context(user_data_dir=str(BROWSER_PROFILE_DIR), headless=False, viewport={"width":1440,"height":1000})
            page = context.pages[0] if context.pages else context.new_page()
            try:
                page.goto(target.application_url, wait_until="domcontentloaded", timeout=60000)
                authorize_target(page.url)
                adapter = adapter_for_url(page.url)
                result = fill_application_form(page, browser_profile, adapter.final_submit_texts)
                page.screenshot(path=str(screenshot), full_page=True)
                print("CONTROLLED BROWSER REHEARSAL: COMPLETE")
                print(f"Target: {target.employer} | {target.title}")
                print(f"ATS: {adapter.name}")
                print(f"Fields filled: {result.filled}")
                print(f"Required unanswered: {len(result.required_unanswered)}")
                print(f"Restricted questions: {len(result.restricted_questions)}")
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

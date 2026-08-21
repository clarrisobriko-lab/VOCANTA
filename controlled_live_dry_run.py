from __future__ import annotations

from automation.application_pipeline import profile_for_package, validate_browser_documents
from automation.idempotency import application_idempotency_key, stable_hash
from automation.live_test_target import PERMITFLOW_ADMINISTRATIVE_ASSISTANT, authorize_target, canonical_url
from automation.package_builder import build_application_package
from automation.profile import load_profile
from automation.tailoring import tailor_documents
from agents.scorer import Scorer
from core.database import Database
from core.models import Job


def _find_target(database: Database):
    target = canonical_url(PERMITFLOW_ADMINISTRATIVE_ASSISTANT.application_url)
    rows = database.connection.execute(
        "SELECT id, company, title, location, source, url, description, salary, employment_type, score, status FROM jobs ORDER BY id DESC"
    ).fetchall()
    for row in rows:
        if canonical_url(row["url"]) == target:
            return row
    raise RuntimeError("Dry run blocked: controlled live target is not in the VOCANTA database. Run discovery/intake first.")


def _row_to_job(row) -> Job:
    return Job(
        company=row["company"], title=row["title"], location=row["location"], source=row["source"],
        url=PERMITFLOW_ADMINISTRATIVE_ASSISTANT.application_url, description=row["description"] or "",
        salary=row["salary"] or "", employment_type=row["employment_type"] or "", score=int(row["score"] or 0),
    )


def main() -> int:
    target = PERMITFLOW_ADMINISTRATIVE_ASSISTANT
    authorize_target(target.application_url)
    profile = load_profile()
    database = Database()
    try:
        row = _find_target(database)
        authorize_target(row["url"])
        job = _row_to_job(row)
        decision = Scorer().evaluate(job)
        if not decision.should_apply:
            raise RuntimeError(f"Dry run blocked by application scoring: {decision.reason}")

        documents = tailor_documents(job, int(row["id"]), profile)
        package = build_application_package(job, documents, decision)
        browser_profile = profile_for_package(profile, package)
        validate_browser_documents(browser_profile)

        profile_hash = stable_hash(profile)
        document_hash = stable_hash({
            "cv_pdf": str(package.cv_pdf),
            "cover_letter_pdf": str(package.cover_letter_pdf),
            "job_url": target.application_url,
        })
        key = application_idempotency_key(target.application_url, profile_hash, document_hash)

        print("CONTROLLED LIVE DRY RUN: READY")
        print(f"Target: {target.employer} | {target.title}")
        print(f"ATS: {target.allowed_ats}")
        print(f"Job ID: {row['id']}")
        print(f"CV: {package.cv_pdf}")
        print(f"Cover letter: {package.cover_letter_pdf}")
        print(f"Idempotency key: {key}")
        print("Submission: DISABLED. No browser application or final submit action was executed.")
        return 0
    finally:
        database.close()


if __name__ == "__main__":
    raise SystemExit(main())

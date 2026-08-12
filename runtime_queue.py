from automation.application_pipeline import run_application_pipeline
from automation.profile import load_profile
from config.settings import AUTOMATION_MAX_APPLICATIONS_PER_RUN, AUTOMATION_MINIMUM_SCORE
from core.acquisition_audit import record_acquisition_result, reconcile_application_outcome
from core.database import Database
from core.models import Job


def row_to_job(row) -> Job:
    return Job(
        company=row["company"], title=row["title"], location=row["location"],
        source=row["source"], url=row["url"], description=row["description"] or "",
        salary=row["salary"] or "", employment_type=row["employment_type"] or "",
        score=int(row["score"]),
    )


def process_runtime_queue(database: Database, profile, *, pipeline=run_application_pipeline) -> int:
    """Process queued vacancies and durably reconcile every pipeline outcome."""
    candidates = database.list_automation_candidates(
        minimum_score=AUTOMATION_MINIMUM_SCORE,
        limit=AUTOMATION_MAX_APPLICATIONS_PER_RUN,
    )
    submitted = 0
    for row in candidates:
        job = row_to_job(row)
        result = pipeline(job, row["id"], profile)
        record_acquisition_result(database, row["id"], result)

        if not result.decision.should_apply:
            database.record_queue_audit(row["id"], "ATS_PIPELINE", "REJECTED", result.decision.reason)
            continue
        if result.automation is None:
            database.record_queue_audit(row["id"], "ATS_PIPELINE", "REJECTED", "Application pipeline produced no browser result")
            continue

        database.record_automation_attempt(
            row["id"], result.automation.status, result.automation.message, result.automation.screenshot
        )
        final_state = reconcile_application_outcome(database, row["id"], result.automation)
        if final_state == "APPLIED":
            database.record_queue_audit(row["id"], "ATS_PIPELINE", "SUBMITTED", result.decision.reason)
            submitted += 1
        elif final_state == "PREPARING":
            database.record_queue_audit(row["id"], "ATS_PIPELINE", "HUMAN_REQUIRED", result.automation.message)
        else:
            database.record_queue_audit(row["id"], "ATS_PIPELINE", "RETRYABLE", result.automation.message)
    return submitted


def main() -> int:
    profile = load_profile()
    database = Database()
    try:
        process_runtime_queue(database, profile)
        return 0
    finally:
        database.close()


if __name__ == "__main__":
    raise SystemExit(main())

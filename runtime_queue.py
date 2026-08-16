from automation.acquisition_audit import AcquisitionAuditStore, reconcile_application_outcome
from automation.application_pipeline import run_application_pipeline
from automation.profile import load_profile
from config.settings import AUTOMATION_MAX_APPLICATIONS_PER_RUN, AUTOMATION_MINIMUM_SCORE
from core.database import Database
from core.models import Job
from core.outcome_store import record_outcome
from core.retry_queue import clear_retry, due_retries, retire_retry, schedule_retry
from intelligence.application_outcomes import classify_outcome


def row_to_job(row) -> Job:
    return Job(company=row["company"], title=row["title"], location=row["location"], source=row["source"], url=row["url"], description=row["description"] or "", salary=row["salary"] or "", employment_type=row["employment_type"] or "", score=int(row["score"]))


def _candidate_rows(database: Database):
    normal = list(database.list_automation_candidates(minimum_score=AUTOMATION_MINIMUM_SCORE, limit=AUTOMATION_MAX_APPLICATIONS_PER_RUN))
    seen = {int(row["id"]) for row in normal}
    remaining = max(0, AUTOMATION_MAX_APPLICATIONS_PER_RUN - len(normal))
    if remaining:
        for retry in due_retries(database.connection, limit=remaining):
            if retry.job_id in seen: continue
            row = database.connection.execute("SELECT * FROM jobs WHERE id=? AND applied=0", (retry.job_id,)).fetchone()
            if row is not None: normal.append(row); seen.add(retry.job_id)
    return normal


def process_runtime_queue(database: Database, profile, *, pipeline=run_application_pipeline) -> int:
    candidates = _candidate_rows(database); audit = AcquisitionAuditStore(database); submitted = 0
    for row in candidates:
        job = row_to_job(row); result = pipeline(job, row["id"], profile)
        package_path = str(result.package.archive) if result.package is not None else ""
        automation_status = result.automation.status if result.automation is not None else ""
        audit.record(row["id"], result.decision, package_path=package_path, automation_status=automation_status)
        if not result.decision.should_apply:
            retire_retry(database.connection, row["id"], "scorer no longer approves application")
            database.record_queue_audit(row["id"], "ATS_PIPELINE", "REJECTED", result.decision.reason); continue
        if result.automation is None:
            retire_retry(database.connection, row["id"], "pipeline produced no browser result")
            database.record_queue_audit(row["id"], "ATS_PIPELINE", "REJECTED", "Application pipeline produced no browser result"); continue
        database.record_automation_attempt(row["id"], result.automation.status, result.automation.message, result.automation.screenshot)
        outcome = classify_outcome(result.automation); record_outcome(database.connection, row["id"], outcome)
        final_state = reconcile_application_outcome(database, row["id"], result.automation)
        if outcome.applied or final_state == "APPLIED":
            clear_retry(database.connection, row["id"]); database.record_queue_audit(row["id"], "ATS_PIPELINE", "SUBMITTED", outcome.reason or result.decision.reason); submitted += 1
        elif outcome.human_required or final_state == "PREPARING":
            retire_retry(database.connection, row["id"], "human action required"); database.record_queue_audit(row["id"], "ATS_PIPELINE", "HUMAN_REQUIRED", outcome.reason or result.automation.message)
        elif outcome.retry_later:
            scheduled = schedule_retry(database.connection, row["id"], outcome.reason)
            database.record_queue_audit(row["id"], "ATS_PIPELINE", "RETRYABLE" if scheduled else "RETIRED", outcome.reason)
        else:
            retire_retry(database.connection, row["id"], outcome.reason); database.record_queue_audit(row["id"], "ATS_PIPELINE", "FAILED", outcome.reason or result.automation.message)
    return submitted


def main() -> int:
    profile = load_profile(); database = Database()
    try: process_runtime_queue(database, profile); return 0
    finally: database.close()


if __name__ == "__main__": raise SystemExit(main())

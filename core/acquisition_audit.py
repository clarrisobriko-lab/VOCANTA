import json
from datetime import datetime, timezone


SUBMITTED_STATUSES = {"AUTO_SUBMITTED", "SUBMITTED", "CONFIRMED"}
HUMAN_STATUSES = {"READY_TO_REVIEW", "HUMAN_VERIFICATION", "MANUAL_REQUIRED"}


def ensure_acquisition_schema(database) -> None:
    with database.connection:
        database.connection.execute(
            """
            CREATE TABLE IF NOT EXISTS acquisition_decisions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                job_id INTEGER NOT NULL,
                composite_score INTEGER NOT NULL,
                base_score INTEGER NOT NULL,
                ats_score INTEGER NOT NULL,
                should_apply INTEGER NOT NULL,
                matched_skills TEXT NOT NULL DEFAULT '[]',
                missing_skills TEXT NOT NULL DEFAULT '[]',
                reason TEXT NOT NULL DEFAULT '',
                package_path TEXT NOT NULL DEFAULT '',
                automation_status TEXT NOT NULL DEFAULT '',
                decided_at TEXT NOT NULL,
                FOREIGN KEY(job_id) REFERENCES jobs(id) ON DELETE CASCADE
            )
            """
        )
        database.connection.execute(
            "CREATE INDEX IF NOT EXISTS idx_acquisition_decisions_job ON acquisition_decisions(job_id)"
        )


def record_acquisition_result(database, job_id: int, result) -> int:
    """Persist the pipeline decision, package location and browser outcome."""
    ensure_acquisition_schema(database)
    package_path = str(result.package.archive) if result.package is not None else ""
    automation_status = result.automation.status.strip().upper() if result.automation is not None else ""
    with database.connection:
        cursor = database.connection.execute(
            """
            INSERT INTO acquisition_decisions(
                job_id, composite_score, base_score, ats_score, should_apply,
                matched_skills, missing_skills, reason, package_path,
                automation_status, decided_at
            ) VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                job_id, result.decision.score, result.decision.base_score,
                result.decision.ats_score, int(result.decision.should_apply),
                json.dumps(list(result.decision.matched_skills)),
                json.dumps(list(result.decision.missing_skills)),
                result.decision.reason, package_path, automation_status,
                datetime.now(timezone.utc).isoformat(),
            ),
        )
    return int(cursor.lastrowid)


def reconcile_application_outcome(database, job_id: int, automation) -> str:
    """Update job state only when the browser outcome provides appropriate evidence."""
    status = automation.status.strip().upper()
    message = automation.message.strip()
    if status in SUBMITTED_STATUSES:
        database.update_application(job_id, "APPLIED", notes=message)
        return "APPLIED"
    if status in HUMAN_STATUSES:
        database.update_application(job_id, "PREPARING", notes=message)
        return "PREPARING"
    # Failure, blocked and unknown outcomes must remain retryable and must never count as applications.
    current = database.get_job(job_id)
    if current is not None and current["status"] == "PREPARING":
        database.update_application(job_id, "NEW", notes=message)
    return database.get_job(job_id)["status"] if database.get_job(job_id) is not None else "NEW"

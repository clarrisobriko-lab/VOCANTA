from __future__ import annotations

from automation.application_pipeline import run_application_pipeline
from automation.idempotency import application_idempotency_key, stable_hash
from automation.live_test_target import PERMITFLOW_ADMINISTRATIVE_ASSISTANT, authorize_target, canonical_url
from automation.profile import load_profile
from core.database import Database
from core.models import Job


def _find_target(database: Database):
    target = canonical_url(PERMITFLOW_ADMINISTRATIVE_ASSISTANT.application_url)
    rows = database.connection.execute(
        """
        SELECT id, company, title, location, source, url, description,
               salary, employment_type, score, status
        FROM jobs
        ORDER BY id DESC
        """
    ).fetchall()
    for row in rows:
        if canonical_url(row["url"]) == target:
            return row
    raise RuntimeError(
        "Controlled live target is not in the VOCANTA database. Run normal discovery/intake first; no substitute vacancy will be used."
    )


def _row_to_job(row) -> Job:
    return Job(
        company=row["company"],
        title=row["title"],
        location=row["location"],
        source=row["source"],
        url=PERMITFLOW_ADMINISTRATIVE_ASSISTANT.application_url,
        description=row["description"] or "",
        salary=row["salary"] or "",
        employment_type=row["employment_type"] or "",
        score=int(row["score"] or 0),
    )


def main() -> int:
    target = PERMITFLOW_ADMINISTRATIVE_ASSISTANT
    authorize_target(target.application_url)
    profile = load_profile()
    database = Database()
    try:
        row = _find_target(database)
        authorize_target(row["url"])

        prior = database.connection.execute(
            "SELECT id, status FROM application_runs WHERE job_id = ? ORDER BY id DESC LIMIT 1",
            (row["id"],),
        ).fetchone()
        if prior is not None:
            raise RuntimeError(
                f"Controlled live submission blocked: application run {prior['id']} already exists with status {prior['status']}."
            )

        prior_attempt = database.connection.execute(
            """
            SELECT id, status FROM automation_attempts
            WHERE job_id = ? AND status IN ('AUTO_SUBMITTED', 'SUBMITTED', 'UNKNOWN')
            ORDER BY id DESC LIMIT 1
            """,
            (row["id"],),
        ).fetchone()
        if prior_attempt is not None:
            raise RuntimeError(
                f"Controlled live submission blocked: prior terminal or ambiguous attempt {prior_attempt['id']} has status {prior_attempt['status']}."
            )

        profile_hash = stable_hash(profile)
        document_hash = "CONTROLLED_LIVE_PACKAGE_PENDING"
        idempotency_key = application_idempotency_key(target.application_url, profile_hash, document_hash)
        run, claimed = database.claim_application_run(
            row["id"], idempotency_key, profile_hash, document_hash
        )
        if not claimed:
            raise RuntimeError("Controlled live submission blocked: idempotency claim already exists.")

        job = _row_to_job(row)
        result = run_application_pipeline(
            job,
            row["id"],
            profile,
            database=database,
            application_run_id=int(run["id"]),
        )

        automation = result.automation
        if automation is None:
            database.update_application_run(idempotency_key, "BLOCKED", last_error=result.decision.reason)
            raise RuntimeError(f"Controlled live target did not pass application scoring: {result.decision.reason}")

        outcome = automation.status.upper()
        mapped = {
            "SUBMITTED": "SUBMITTED",
            "SUCCESS": "SUBMITTED",
            "AUTO_SUBMITTED": "CONFIRMED",
            "HUMAN_REQUIRED": "HUMAN_VERIFICATION",
            "MANUAL_REQUIRED": "MANUAL_REQUIRED",
            "REQUEUE": "UNKNOWN",
            "UNKNOWN": "UNKNOWN",
            "FAILED": "FAILED",
        }.get(outcome, "UNKNOWN")
        database.update_application_run(
            idempotency_key,
            mapped,
            confirmation_text=getattr(automation, "confirmation_text", "") or "",
            confirmation_url=getattr(automation, "confirmation_url", "") or "",
            screenshot_path=getattr(automation, "screenshot_path", "") or getattr(automation, "screenshot", "") or "",
            active_url=getattr(automation, "active_url", "") or target.application_url,
            last_error=automation.message if mapped in {"FAILED", "UNKNOWN"} else "",
        )
        database.record_automation_attempt(
            row["id"], outcome, automation.message,
            getattr(automation, "screenshot_path", "") or getattr(automation, "screenshot", "") or "",
        )

        print(f"Controlled live result: {outcome}")
        print(f"Evidence: {result.evidence_path or 'not created'}")
        return 0 if mapped in {"SUBMITTED", "CONFIRMED", "HUMAN_VERIFICATION", "MANUAL_REQUIRED"} else 2
    finally:
        database.close()


if __name__ == "__main__":
    raise SystemExit(main())

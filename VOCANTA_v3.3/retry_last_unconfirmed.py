"""Safely reopen the latest unconfirmed Greenhouse application for one retry.

This command is deliberately conservative. It refuses to touch any job carrying
submission evidence, an applied flag, or a confirmed application run. It exists
for controlled acceptance testing and recovery from a browser or form failure.
"""
from __future__ import annotations

from datetime import datetime, timezone

from rich.console import Console
from rich.panel import Panel

from core.database import Database


UNCONFIRMED_RUN_STATES = {
    "CREATED",
    "PREPARING",
    "FORM_FILLED",
    "READY_TO_REVIEW",
    "HUMAN_VERIFICATION",
    "MANUAL_REQUIRED",
    "UNKNOWN",
    "FAILED",
    "BLOCKED",
}


def latest_retryable_job(database: Database):
    return database.connection.execute(
        """
        SELECT j.id, j.company, j.title, j.url, j.applied,
               r.status AS run_status, r.confirmation_text, r.confirmation_url,
               r.updated_at
        FROM jobs AS j
        JOIN application_runs AS r ON r.job_id = j.id
        WHERE lower(j.source) = 'greenhouse'
          AND r.status IN ({})
        ORDER BY r.updated_at DESC, r.id DESC
        LIMIT 1
        """.format(",".join("?" for _ in UNCONFIRMED_RUN_STATES)),
        tuple(sorted(UNCONFIRMED_RUN_STATES)),
    ).fetchone()


def authorize_retry(database: Database, job_id: int) -> None:
    job = database.connection.execute(
        "SELECT id, applied FROM jobs WHERE id = ?", (job_id,)
    ).fetchone()
    if job is None:
        raise ValueError("Job not found")
    if int(job["applied"] or 0) == 1:
        raise ValueError("Retry refused because this job is already marked applied")

    evidence = database.connection.execute(
        """
        SELECT 1
        FROM application_runs
        WHERE job_id = ?
          AND (status = 'CONFIRMED'
               OR trim(confirmation_text) != ''
               OR trim(confirmation_url) != '')
        LIMIT 1
        """,
        (job_id,),
    ).fetchone()
    if evidence is not None:
        raise ValueError("Retry refused because submission evidence exists")

    attempt_evidence = database.connection.execute(
        """
        SELECT 1 FROM automation_attempts
        WHERE job_id = ? AND status IN ('AUTO_SUBMITTED', 'SUBMITTED')
        LIMIT 1
        """,
        (job_id,),
    ).fetchone()
    if attempt_evidence is not None:
        raise ValueError("Retry refused because a submitted attempt exists")

    now = datetime.now(timezone.utc).isoformat()
    with database.connection:
        prior = database.connection.execute(
            "SELECT group_concat(status, ', ') AS statuses FROM application_runs WHERE job_id = ?",
            (job_id,),
        ).fetchone()
        prior_statuses = (prior["statuses"] or "none") if prior else "none"
        database.connection.execute("DELETE FROM notification_deliveries WHERE job_id = ?", (job_id,))
        database.connection.execute("DELETE FROM human_action_queue WHERE job_id = ?", (job_id,))
        database.connection.execute("DELETE FROM automation_attempts WHERE job_id = ?", (job_id,))
        database.connection.execute("DELETE FROM application_runs WHERE job_id = ?", (job_id,))
        database.connection.execute(
            "UPDATE jobs SET status = 'NEW', applied = 0, applied_date = NULL, follow_up_date = NULL, updated_at = ? WHERE id = ?",
            (now, job_id),
        )
        database.connection.execute(
            """
            INSERT INTO automation_queue_audit(queue_id, job_id, stage, decision, reason, created_at)
            VALUES(lower(hex(randomblob(16))), ?, 'SAFE_RETRY', 'ACCEPTED', ?, ?)
            """,
            (job_id, f"User-authorised retry of unconfirmed run states: {prior_statuses}", now),
        )


def main() -> int:
    console = Console()
    database = Database()
    try:
        row = latest_retryable_job(database)
        if row is None:
            console.print(Panel("No unconfirmed Greenhouse application is available for retry.", title="Nothing to Retry", border_style="yellow"))
            return 0
        authorize_retry(database, int(row["id"]))
        console.print(Panel(
            f"{row['company']}\n{row['title']}\n\nThe previous unconfirmed run was safely cleared. Run start_vocanta.bat to try this application once more.",
            title="Safe Retry Authorised",
            border_style="green",
        ))
        return 0
    except ValueError as exc:
        console.print(Panel(str(exc), title="Retry Refused", border_style="red"))
        return 1
    finally:
        database.close()


if __name__ == "__main__":
    raise SystemExit(main())

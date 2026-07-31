from datetime import date, timedelta
from pathlib import Path

from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from automation.idempotency import (
    application_idempotency_key,
    combined_document_hash,
    stable_hash,
)
from intelligence.eligibility import (
    assess_eligibility,
    blocked_automation_domain,
    discovery_only_reason,
)
from intelligence.assessment import assess_job
from intelligence.opportunity import assess_opportunity
from notifications.emailer import (
    AUTH_MODE_APP_PASSWORD,
    DeliveryResult,
    load_email_settings,
    notification_dedup_key,
    send_human_completion_email,
)
from notifications.outbox import retry_email_outbox
from automation.browser import BrowserApplicationEngine
from automation.preflight import assess_application_url
from automation.profile import load_profile
from automation.tailoring import tailor_documents, with_tailored_documents
from config.settings import (
    AUTOMATION_MAX_APPLICATIONS_PER_RUN,
    AUTOMATION_MINIMUM_SCORE,
    DEFAULT_FOLLOW_UP_DAYS,
    HIGH_VALUE_MINIMUM_OPPORTUNITY_SCORE,
    HIGH_VALUE_MINIMUM_SCORE,
)
from core.application_exporter import export_applications
from core.database import Database
from core.models import Job
from core.revalidation import revalidate_existing_jobs


def row_to_job(row) -> Job:
    return Job(
        company=row["company"],
        title=row["title"],
        location=row["location"],
        source=row["source"],
        url=row["url"],
        description=row["description"] or "",
        salary=row["salary"] or "",
        employment_type=row["employment_type"] or "",
        score=int(row["score"]),
    )



def deliver_human_action_notification(
    *,
    database: Database,
    row,
    documents,
    intelligence,
    opportunity,
    status: str,
    reason: str,
    active_url: str,
    screenshot: str,
) -> DeliveryResult:
    attachment_paths = [
        documents.resume_path,
        documents.cover_letter_path,
    ]
    if documents.certificate_path:
        attachment_paths.append(documents.certificate_path)
    if screenshot:
        attachment_paths.append(Path(screenshot))

    email_configuration = load_email_settings()
    recipient = (
        email_configuration[0].recipient_email
        if email_configuration
        else ""
    )
    auth_mode = (
        email_configuration[0].auth_mode
        if email_configuration
        else AUTH_MODE_APP_PASSWORD
    )
    delivery_key = notification_dedup_key(
        job_id=row["id"],
        status=status,
        recipient=recipient,
        attachments=tuple(attachment_paths),
    )
    existing_delivery, delivery_claimed = database.claim_notification_delivery(
        row["id"],
        delivery_key,
        auth_mode,
    )
    if delivery_claimed:
        database.update_notification_delivery(delivery_key, "SENDING")
        delivery = send_human_completion_email(
            job_id=row["id"],
            company=row["company"],
            title=row["title"],
            job_url=active_url or row["url"],
            status=status,
            reason=reason,
            score=int(row["score"]),
            opportunity_score=opportunity.score,
            recommendation=intelligence.recommendation,
            sponsorship=intelligence.sponsorship_label,
            relocation=intelligence.relocation_label,
            rationale=opportunity.rationale,
            attachments=attachment_paths,
        )
        notification_status = (
            "SENT"
            if delivery.delivered
            else "AUTH_REQUIRED"
            if delivery.error_code == "AUTH_REQUIRED"
            else "OUTBOX"
        )
        database.update_notification_delivery(
            delivery_key,
            notification_status,
            error_code=delivery.error_code,
            outbox_path=(
                delivery.location if delivery.method == "OUTBOX" else ""
            ),
        )
        return delivery

    return DeliveryResult(
        delivered=existing_delivery["status"] == "SENT",
        method="RECORDED",
        location=existing_delivery["outbox_path"],
        message=(
            "Notification already sent; duplicate suppressed."
            if existing_delivery["status"] == "SENT"
            else "Notification delivery is already recorded for retry."
        ),
        error_code=existing_delivery["last_error_code"],
    )


def main() -> int:
    console = Console()

    try:
        profile = load_profile()
    except (FileNotFoundError, ValueError) as exc:
        console.print(
            Panel(
                str(exc),
                title="Applicant Profile Required",
                border_style="red",
            )
        )
        return 1

    database = Database()
    summary: list[tuple[str, str, str]] = []
    profile_hash = stable_hash(profile)

    configured_email = load_email_settings()
    if configured_email:
        retry_result = retry_email_outbox(*configured_email)
        if retry_result.attempted:
            console.print(
                f"[dim]Email outbox recovery: {retry_result.sent} sent, "
                f"{retry_result.failed} still pending.[/dim]"
            )

    try:
        repaired_statuses = database.repair_job_statuses("AUTOMATED_APPLY_START")
        for row in repaired_statuses:
            console.print(
                f"[yellow]Status repaired:[/yellow] Job {row['id']} | "
                f"FOLLOW_UP -> NEW | {row['company']} | no confirmed submission evidence"
            )
        revalidate_existing_jobs(database)
        candidates = database.list_automation_candidates(
            minimum_score=AUTOMATION_MINIMUM_SCORE,
            limit=AUTOMATION_MAX_APPLICATIONS_PER_RUN,
        )

        if not candidates:
            database.audit_automation_queue(AUTOMATION_MINIMUM_SCORE)
            console.print(
                Panel(
                    "No new direct Greenhouse application is ready in this run. "
                    "Unsupported sources were never scouted, and jobs with terminal "
                    "application history were suppressed before queue construction.",
                    title="No New Application Candidate",
                    border_style="yellow",
                )
            )
            return 0

        selected = []
        for candidate in candidates:
            preflight = assess_application_url(candidate["url"])
            if preflight.allowed:
                selected.append(candidate)
                break
            database.record_automation_attempt(
                candidate["id"], "SKIPPED_SOURCE", preflight.reason, ""
            )
            database.record_queue_audit(
                candidate["id"], "PREFLIGHT", "REJECTED", preflight.reason
            )

        if not selected:
            console.print(Panel(
                "No supported Greenhouse application is ready. Blocked, marketplace, "
                "and unsupported URLs were rejected before browser launch.",
                title="No Safe Application Candidate", border_style="yellow"
            ))
            return 0

        candidates = selected
        console.print(
            Panel(
                "1 verified Greenhouse candidate selected. VOCANTA will complete the "
                "form, upload documents, pause only for protected personal responses, "
                "and record success only after confirmation evidence.",
                title="Professional Application Run",
                border_style="cyan",
            )
        )

        for row in candidates:
            queue_id = row["queue_id"]
            console.print(
                f"[dim]Queue ID {queue_id}: ACCEPTED into automation queue[/dim]"
            )
            job = row_to_job(row)
            eligibility = assess_eligibility(job)
            intelligence = assess_job(job)
            opportunity = assess_opportunity(
                job,
                intelligence,
                HIGH_VALUE_MINIMUM_SCORE,
                HIGH_VALUE_MINIMUM_OPPORTUNITY_SCORE,
            )

            blocked_domain = blocked_automation_domain(row["url"])
            discovery_only = discovery_only_reason(job)
            if discovery_only:
                database.record_automation_attempt(
                    row["id"],
                    "SKIPPED_SOURCE",
                    discovery_only,
                    "",
                )
                database.record_queue_audit(
                    row["id"], "PRE_BROWSER", "REJECTED", discovery_only
                )
                summary.append((row["company"], "SKIPPED_SOURCE", discovery_only))
                continue
            if blocked_domain:
                message = (
                    f"Source skipped before browser launch: {blocked_domain}. "
                    "Cloudflare-protected sources are disabled."
                )
                database.record_automation_attempt(
                    row["id"],
                    "SKIPPED_SOURCE",
                    message,
                    "",
                )
                database.record_queue_audit(
                    row["id"], "PRE_BROWSER", "REJECTED", message
                )
                summary.append((row["company"], "SKIPPED_SOURCE", message))
                continue

            if eligibility.verdict in {"BLOCK", "REVIEW"}:
                skip_reason = (
                    f"Eligibility {eligibility.verdict}: "
                    f"{eligibility.primary_reason}"
                )
                database.record_automation_attempt(
                    row["id"],
                    "SKIPPED",
                    skip_reason,
                    "",
                )
                database.record_queue_audit(
                    row["id"], "PRE_BROWSER", "REJECTED", skip_reason
                )
                summary.append(
                    (
                        row["company"],
                        "SKIPPED",
                        eligibility.primary_reason,
                    )
                )
                continue

            database.record_queue_audit(
                row["id"], "PRE_BROWSER", "ACCEPTED",
                f"Queue {queue_id} passed all pre-browser filters"
            )
            console.print(
                f"\n[bold]{row['company']}[/bold] · {row['title']} · {row['score']}"
            )
            documents = tailor_documents(job, row["id"], profile)
            tailored_profile = with_tailored_documents(profile, documents)
            document_hash = combined_document_hash(
                (
                    documents.resume_path,
                    documents.cover_letter_path,
                    documents.certificate_path,
                )
            )
            idempotency_key = application_idempotency_key(
                row["url"],
                profile_hash,
                document_hash,
            )
            existing_run, claimed = database.claim_application_run(
                row["id"],
                idempotency_key,
                profile_hash,
                document_hash,
            )
            if not claimed:
                message = (
                    "Application run already exists with state "
                    f"{existing_run['status']}; automatic retry suppressed."
                )
                database.record_automation_attempt(
                    row["id"],
                    "SKIPPED_DUPLICATE",
                    message,
                    existing_run["screenshot_path"],
                )
                database.record_queue_audit(
                    row["id"], "CLAIM", "REJECTED", message
                )
                summary.append((row["company"], "SKIPPED_DUPLICATE", message))
                continue

            database.update_application_run(idempotency_key, "PREPARING")

            def persist_state(status: str, details: dict[str, str]) -> None:
                database.update_application_run(
                    idempotency_key,
                    status,
                    confirmation_text=details.get("confirmation_text", ""),
                    confirmation_url=details.get("confirmation_url", ""),
                    screenshot_path=details.get("screenshot_path", ""),
                    last_error=details.get("last_error", ""),
                    active_url=details.get("active_url", ""),
                )

            immediate_delivery: dict[str, DeliveryResult] = {}

            def notify_human_action(
                status: str,
                reason: str,
                screenshot_path: str,
                active_url: str,
            ) -> None:
                delivery = deliver_human_action_notification(
                    database=database,
                    row=row,
                    documents=documents,
                    intelligence=intelligence,
                    opportunity=opportunity,
                    status=status,
                    reason=reason,
                    active_url=active_url,
                    screenshot=screenshot_path,
                )
                immediate_delivery["result"] = delivery
                console.print(
                    f"[bold magenta]Human completion notification:[/bold magenta] "
                    f"{delivery.message} {delivery.location}"
                )

            engine = BrowserApplicationEngine(
                tailored_profile,
                state_callback=persist_state,
                human_action_callback=notify_human_action,
            )
            console.print(
                f"[dim]Tailored documents: {documents.folder} | "
                f"Track: {documents.category}[/dim]"
            )
            result = engine.apply(row["url"], row["id"])
            run = database.get_application_run(idempotency_key)
            target_state = {
                "AUTO_SUBMITTED": "CONFIRMED",
                "READY_TO_REVIEW": "READY_TO_REVIEW",
                "HUMAN_VERIFICATION": "HUMAN_VERIFICATION",
                "MANUAL_REQUIRED": "MANUAL_REQUIRED",
                "UNKNOWN": "UNKNOWN",
                "FAILED": "FAILED",
                "SKIPPED_SOURCE": "FAILED",
            }.get(result.status)
            if target_state and run is not None and run["status"] != target_state:
                database.update_application_run(
                    idempotency_key,
                    target_state,
                    confirmation_text=result.confirmation_text,
                    confirmation_url=result.confirmation_url,
                    screenshot_path=result.screenshot,
                    last_error=result.message if target_state in {"FAILED", "UNKNOWN"} else "",
                )
            database.record_automation_attempt(
                row["id"],
                result.status,
                result.message,
                result.screenshot,
            )

            delivery = immediate_delivery.get("result")
            if result.status in {
                "READY_TO_REVIEW",
                "HUMAN_VERIFICATION",
                "MANUAL_REQUIRED",
                "UNKNOWN",
                "FAILED",
            } and delivery is None:
                delivery = deliver_human_action_notification(
                    database=database,
                    row=row,
                    documents=documents,
                    intelligence=intelligence,
                    opportunity=opportunity,
                    status=result.status,
                    reason=result.message,
                    active_url=(
                        run["active_url"]
                        if run is not None and run["active_url"]
                        else row["url"]
                    ),
                    screenshot=result.screenshot,
                )
                console.print(
                    f"[bold magenta]Human completion notification:[/bold magenta] "
                    f"{delivery.message} {delivery.location}"
                )

            if result.status in {"READY_TO_REVIEW", "HUMAN_VERIFICATION", "MANUAL_REQUIRED", "UNKNOWN", "FAILED"}:
                database.queue_human_action(
                    job_id=row["id"],
                    status=result.status,
                    reason=result.message,
                    job_score=int(row["score"]),
                    opportunity_score=opportunity.score,
                    email_status=(
                        "SENT"
                        if delivery and delivery.delivered
                        else "AUTH_REQUIRED"
                        if delivery and delivery.error_code == "AUTH_REQUIRED"
                        else "OUTBOX"
                        if delivery
                        else "NOT_SENT"
                    ),
                    email_location=delivery.location if delivery else "",
                )

            run = database.get_application_run(idempotency_key)
            if result.status == "AUTO_SUBMITTED" and run and run["status"] == "CONFIRMED":
                follow_up = (
                    date.today() + timedelta(days=DEFAULT_FOLLOW_UP_DAYS)
                ).isoformat()
                database.mark_applied_with_follow_up(
                    job_id=row["id"],
                    notes=(
                        f"Automatically submitted or confirmed by VOCANTA. "
                        f"Screenshot: {result.screenshot}"
                    ),
                    follow_up_date=follow_up,
                )

            summary.append((row["company"], result.status, result.message))
            console.print(f"[bold]{result.status}[/bold] · {result.message}")

        export_applications(database.list_applications())

        table = Table(title="Automation Summary", expand=True)
        table.add_column("Company")
        table.add_column("Result")
        table.add_column("Details", ratio=4)
        for company, status, message in summary:
            table.add_row(company, status, message)
        console.print(table)
        return 0
    finally:
        database.close()


if __name__ == "__main__":
    raise SystemExit(main())

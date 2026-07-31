import os
import re
import webbrowser
from datetime import date, datetime, timedelta
from pathlib import Path

from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from agents.eligibility import assess_eligibility
from automation.profile import load_profile
from automation.tailoring import tailor_documents
from config.settings import (
    APPLICATION_QUEUE_LIMIT,
    APPLICATIONS_DIR,
    APP_DISPLAY_NAME,
    DEFAULT_FOLLOW_UP_DAYS,
    SHORTLIST_SCORE,
)
from core.application_exporter import export_applications
from core.database import Database
from core.models import Job


def safe_name(value: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9._-]+", "_", value.strip())
    return cleaned.strip("_")[:80] or "application"


def row_to_job(row) -> Job:
    return Job(
        company=row["company"],
        title=row["title"],
        location=row["location"],
        source=row["source"],
        url=row["url"],
        description=row["description"] or "",
        employment_type=row["employment_type"] or "",
        score=int(row["score"]),
    )


def create_application_pack(job) -> Path:
    stamp = datetime.now().strftime("%Y%m%d")
    folder = APPLICATIONS_DIR / (
        f"{job['id']}_{safe_name(job['company'])}_{safe_name(job['title'])}_{stamp}"
    )
    folder.mkdir(parents=True, exist_ok=True)

    checklist = folder / "APPLICATION_CHECKLIST.md"
    checklist.write_text(
        f"""# {job['title']}

Company: {job['company']}
Score: {job['score']}
Location: {job['location']}
Source: {job['source']}
Application URL: {job['url']}

## Before submitting

- [ ] Confirm the role accepts applicants from my location
- [ ] Confirm visa or work-authorisation requirements
- [ ] Tailor CV headline and professional summary
- [ ] Match experience bullets to the essential criteria
- [ ] Prepare a role-specific cover letter where requested
- [ ] Check spelling, dates, contact details, and document names
- [ ] Save the final CV and cover letter in this folder
- [ ] Submit the application
- [ ] Record the submission in VOCANTA as APPLIED
- [ ] Confirm the follow-up date

## Application record

Submission date:
Platform:
Contact person:
Follow-up date:
Outcome:
Notes:
""",
        encoding="utf-8",
    )
    return folder


def show_queue(console: Console, rows) -> None:
    table = Table(title=f"{APP_DISPLAY_NAME} Real Application Queue", expand=True)
    table.add_column("ID", justify="right", width=4, no_wrap=True)
    table.add_column("Score", justify="right", width=5, no_wrap=True)
    table.add_column("Company", ratio=2, overflow="ellipsis", no_wrap=True)
    table.add_column("Role", ratio=4, overflow="ellipsis", no_wrap=True)
    table.add_column("Visa", width=7, no_wrap=True)
    table.add_column("Reloc.", width=7, no_wrap=True)
    table.add_column("Track", width=9, no_wrap=True)
    table.add_column("Status", ratio=2, overflow="ellipsis", no_wrap=True)

    for row in rows:
        assessment = assess_eligibility(row_to_job(row))
        visa_style = {
            "YES": "green",
            "NO": "red",
            "UNKNOWN": "yellow",
        }[assessment.sponsorship]
        relocation_style = "green" if assessment.relocation == "YES" else "yellow"
        verdict_style = {
            "PRIORITY": "bright_green",
            "APPLY": "cyan",
            "RESEARCH": "red",
        }[assessment.verdict]

        table.add_row(
            str(row["id"]),
            str(row["score"]),
            row["company"],
            row["title"],
            f"[{visa_style}]{assessment.sponsorship}[/]",
            f"[{relocation_style}]{assessment.relocation}[/]",
            f"[{verdict_style}]{assessment.verdict}[/]",
            row["status"],
        )
    console.print(table)


def confirm_application(
    console: Console,
    database: Database,
    job,
    folder: Path,
) -> None:
    default_follow_up = (
        date.today() + timedelta(days=DEFAULT_FOLLOW_UP_DAYS)
    ).isoformat()

    console.print(
        Panel(
            "After submitting in the browser:\n\n"
            "[bold]A[/bold] = mark APPLIED now\n"
            "[bold]P[/bold] = leave as PREPARING\n"
            "[bold]R[/bold] = mark for RESEARCH",
            title="Record Outcome",
            border_style="cyan",
        )
    )
    choice = console.input("Choose A, P, or R: ").strip().lower()

    if choice == "a":
        follow_up = console.input(
            f"Follow-up date [{default_follow_up}]: "
        ).strip() or default_follow_up
        notes = console.input(
            "Application notes, optional: "
        ).strip()
        combined_notes = notes or f"Application submitted. Workspace: {folder.name}"
        database.mark_applied_with_follow_up(
            job_id=job["id"],
            notes=combined_notes,
            follow_up_date=follow_up,
        )
        export_applications(database.list_applications())
        console.print(
            Panel(
                f"Marked APPLIED.\nFollow-up scheduled for {follow_up}.",
                title="Application Recorded",
                border_style="green",
            )
        )
        return

    if choice == "r":
        database.update_application(
            job_id=job["id"],
            status="SHORTLISTED",
            notes=f"Requires eligibility research. Workspace: {folder.name}",
            follow_up_date=None,
        )
        export_applications(database.list_applications())
        console.print("Saved for eligibility research.")
        return

    console.print("Job remains PREPARING.")


def main() -> int:
    console = Console()
    try:
        profile = load_profile()
    except (FileNotFoundError, ValueError) as exc:
        console.print(f"[red]{exc}[/red]")
        return 1
    database = Database()

    try:
        while True:
            rows = database.list_application_candidates(
                minimum_score=SHORTLIST_SCORE,
                limit=APPLICATION_QUEUE_LIMIT,
            )
            os.system("cls" if os.name == "nt" else "clear")

            if not rows:
                console.print(
                    Panel(
                        "No NEW, SHORTLISTED, or PREPARING jobs are available.",
                        title="Application Queue",
                    )
                )
                return 0

            show_queue(console, rows)
            console.print()
            raw = console.input(
                "[bold]Enter a numeric job ID, or press Enter to exit: [/bold]"
            ).strip()
            if not raw:
                return 0
            if not raw.isdigit():
                console.print("Invalid job ID.")
                input("Press Enter to continue: ")
                continue

            job = database.get_job(int(raw))
            if job is None:
                console.print("Job not found.")
                input("Press Enter to continue: ")
                continue

            assessment = assess_eligibility(row_to_job(job))
            console.print(
                Panel(
                    f"[bold]{job['company']}[/bold]\n"
                    f"{job['title']}\n\n"
                    f"Visa sponsorship: {assessment.sponsorship}\n"
                    f"Relocation support: {assessment.relocation}\n"
                    f"Employer type: {assessment.organisation}\n"
                    f"Recommended track: {assessment.verdict}",
                    title="Eligibility Check",
                    border_style="magenta",
                )
            )

            proceed = console.input(
                "Press O to open and prepare, or Enter to return: "
            ).strip().lower()
            if proceed != "o":
                continue

            documents = tailor_documents(row_to_job(job), job["id"], profile)
            folder = documents.folder
            database.update_application(
                job["id"],
                "PREPARING",
                f"Tailored application pack created: {folder.name}",
                None,
            )
            export_applications(database.list_applications())

            console.print(
                Panel(
                    f"Workspace created:\n{folder}\n\n"
                    "The employer page will open now.",
                    title="Application Ready",
                    border_style="green",
                )
            )
            webbrowser.open(job["url"])
            confirm_application(console, database, job, folder)
            input("\nPress Enter to return to the queue: ")
    finally:
        database.close()


if __name__ == "__main__":
    raise SystemExit(main())

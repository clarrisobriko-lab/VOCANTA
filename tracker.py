from datetime import date, datetime, timedelta, timezone
from shutil import get_terminal_size
import webbrowser

from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from config.settings import APP_DISPLAY_NAME, DEFAULT_FOLLOW_UP_DAYS, SHORTLIST_SCORE
from core.application_exporter import export_applications
from core.database import Database, VALID_STATUSES


STATUS_MENU = {
    "1": "SHORTLISTED",
    "2": "PREPARING",
    "3": "APPLIED",
    "4": "FOLLOW_UP",
    "5": "INTERVIEW",
    "6": "REJECTED",
    "7": "OFFER",
}

STATUS_STYLES = {
    "NEW": "cyan",
    "SHORTLISTED": "blue",
    "PREPARING": "bright_blue",
    "APPLIED": "yellow",
    "FOLLOW_UP": "magenta",
    "INTERVIEW": "green",
    "REJECTED": "red",
    "OFFER": "bright_green",
}


def days_since(value: str | None) -> str:
    if not value:
        return ""
    try:
        applied = datetime.fromisoformat(value)
        now = datetime.now(timezone.utc)
        return str(max(0, (now - applied).days))
    except ValueError:
        return ""


def styled_status(status: str) -> str:
    style = STATUS_STYLES.get(status, "white")
    return f"[{style}]{status}[/{style}]"


def show_status_summary(console: Console, database: Database) -> None:
    counts = database.status_counts(SHORTLIST_SCORE)
    summary = "  ".join(
        f"[{STATUS_STYLES.get(status, 'white')}]{status}: {counts.get(status, 0)}[/]"
        for status in (
            "NEW",
            "SHORTLISTED",
            "PREPARING",
            "APPLIED",
            "FOLLOW_UP",
            "INTERVIEW",
            "REJECTED",
            "OFFER",
        )
    )
    console.print(Panel(summary, title=f"{APP_DISPLAY_NAME} Pipeline Status"))


def show_due_follow_ups(console: Console, database: Database) -> None:
    rows = database.list_due_follow_ups()
    if not rows:
        return

    table = Table(title="⚠ FOLLOW UPS DUE", border_style="magenta")
    table.add_column("ID", justify="right")
    table.add_column("Company")
    table.add_column("Role")
    table.add_column("Due")
    table.add_column("Notes")

    for row in rows:
        table.add_row(
            str(row["id"]),
            row["company"],
            row["title"],
            row["follow_up_date"] or "",
            row["notes"] or "",
        )
    console.print(table)


def show_jobs(console: Console, rows, title: str | None = None) -> None:
    width = get_terminal_size((120, 30)).columns
    compact = width < 105
    table = Table(
        title=title or f"{APP_DISPLAY_NAME} Application Tracker",
        expand=True,
    )
    table.add_column("ID", justify="right", width=4, no_wrap=True)
    table.add_column("Score", justify="right", width=5, no_wrap=True)
    table.add_column("Company", ratio=2, overflow="ellipsis", no_wrap=True)
    table.add_column("Title", ratio=5, overflow="ellipsis", no_wrap=True)
    table.add_column("Status", ratio=2, overflow="ellipsis", no_wrap=True)
    if not compact:
        table.add_column("Days", justify="right", width=5, no_wrap=True)

    for row in rows:
        values = [
            str(row["id"]),
            str(row["score"]),
            row["company"],
            row["title"],
            styled_status(row["status"]),
        ]
        if not compact:
            values.append(days_since(row["applied_date"]))
        table.add_row(*values)
    console.print(table)


def show_details(console: Console, job) -> None:
    applied_date = job["applied_date"] or "Not applied"
    follow_up = job["follow_up_date"] or "Not set"
    notes = job["notes"] or "No notes"
    body = (
        f"[bold]Company:[/bold] {job['company']}\n"
        f"[bold]Role:[/bold] {job['title']}\n"
        f"[bold]Score:[/bold] {job['score']}\n"
        f"[bold]Location:[/bold] {job['location']}\n"
        f"[bold]Status:[/bold] {styled_status(job['status'])}\n"
        f"[bold]Applied:[/bold] {applied_date}\n"
        f"[bold]Follow up:[/bold] {follow_up}\n"
        f"[bold]Notes:[/bold] {notes}\n"
        f"[bold]URL:[/bold] {job['url']}"
    )
    console.print(Panel(body, title=f"Job {job['id']}"))


def update_job(console: Console, database: Database, job) -> None:
    console.print(
        "\n1 Shortlisted\n"
        "2 Preparing\n"
        "3 Applied\n"
        "4 Follow Up\n"
        "5 Interview\n"
        "6 Rejected\n"
        "7 Offer"
    )
    choice = input("Choose status: ").strip()
    status = STATUS_MENU.get(choice)
    if status not in VALID_STATUSES:
        console.print("Invalid status.")
        return

    follow_up_date = ""
    if status in {"APPLIED", "FOLLOW_UP"}:
        default_follow_up = (
            date.today() + timedelta(days=DEFAULT_FOLLOW_UP_DAYS)
        ).isoformat()
        follow_up_date = input(
            f"Follow up date [{default_follow_up}]: "
        ).strip() or default_follow_up

    notes = input("Notes, optional: ").strip()
    database.update_application(
        job["id"],
        status,
        notes,
        follow_up_date or None,
    )
    export_applications(database.list_applications())
    console.print(
        f"\nUpdated: {job['company']} · {job['title']} · {status}"
    )


def main() -> int:
    console = Console()
    database = Database()

    try:
        while True:
            console.clear()
            show_due_follow_ups(console, database)
            show_status_summary(console, database)

            rows = database.list_jobs(minimum_score=SHORTLIST_SCORE)
            if not rows:
                console.print("No shortlisted jobs yet. Run run.bat first.")
                return 1

            show_jobs(console, rows)
            command = input(
                "\nEnter job ID, S = search, R = refresh, Enter = exit: "
            ).strip()

            if not command:
                return 0

            if command.lower() == "r":
                continue

            if command.lower() == "s":
                query = input("Search company, role, location, source, or notes: ").strip()
                if not query:
                    continue
                results = database.search_jobs(
                    query,
                    minimum_score=SHORTLIST_SCORE,
                )
                console.clear()
                show_jobs(console, results, title=f"Search Results · {query}")
                input("\nPress Enter to return: ")
                continue

            try:
                job_id = int(command)
            except ValueError:
                console.print("Invalid command.")
                input("Press Enter to continue: ")
                continue

            job = database.get_job(job_id)
            if job is None:
                console.print("Job not found.")
                input("Press Enter to continue: ")
                continue

            console.clear()
            show_details(console, job)
            action = input(
                "\nU = update, O = open job, H = history, Enter = back: "
            ).strip().lower()

            if action == "o":
                webbrowser.open(job["url"])
                continue

            if action == "h":
                history = database.get_history(job_id)
                table = Table(title=f"History · {job['company']} · {job['title']}")
                table.add_column("Changed at")
                table.add_column("From")
                table.add_column("To")
                table.add_column("Notes")
                for row in history:
                    table.add_row(
                        row["changed_at"],
                        row["old_status"] or "",
                        row["new_status"],
                        row["notes"] or "",
                    )
                console.print(table)
                input("\nPress Enter to continue: ")
                continue

            if action == "u":
                update_job(console, database, job)
                input("\nPress Enter to continue: ")
    finally:
        database.close()


if __name__ == "__main__":
    raise SystemExit(main())

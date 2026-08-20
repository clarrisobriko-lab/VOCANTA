import webbrowser
from pathlib import Path

from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt
from rich.table import Table

from config.settings import ACTION_CENTRE_MAX_ITEMS
from core.database import Database
from core.submission_audit import list_submission_evidence


def show_history(console: Console, database: Database) -> None:
    rows = database.connection.execute(
        """
        SELECT e.job_id, j.company, j.title, e.ats, e.outcome, e.recorded_at
        FROM submission_evidence AS e
        JOIN jobs AS j ON j.id = e.job_id
        ORDER BY e.recorded_at DESC, e.id DESC
        LIMIT 100
        """
    ).fetchall()
    console.clear()
    table = Table(expand=True, title="Application History")
    table.add_column("Job")
    table.add_column("Company")
    table.add_column("Role", ratio=3)
    table.add_column("ATS")
    table.add_column("Outcome")
    table.add_column("Recorded")
    for row in rows:
        table.add_row(str(row["job_id"]), row["company"], row["title"], row["ats"], row["outcome"], row["recorded_at"][:19])
    console.print(table)
    answer = Prompt.ask("Job ID for evidence, or Enter to return", default="", show_default=False).strip()
    if not answer.isdigit():
        return
    evidence = list_submission_evidence(database.connection, int(answer))
    if not evidence:
        return
    latest = evidence[0]
    console.print(Panel(
        f"Outcome: {latest['outcome']}\nATS: {latest['ats']}\nRecorded: {latest['recorded_at']}\n"
        f"Package SHA256: {latest['package_sha256']}\nEvidence: {latest['evidence_path']}\n"
        f"Confirmation: {latest['confirmation_url'] or 'None'}\nScreenshot: {latest['screenshot_path'] or 'None'}",
        title=f"Job {answer} Evidence",
    ))
    action = Prompt.ask("E evidence, C confirmation, S screenshot, Enter back", default="", show_default=False).strip().upper()
    if action == "E":
        path = Path(latest["evidence_path"])
        if path.exists():
            webbrowser.open(path.resolve().as_uri())
    elif action == "C" and latest["confirmation_url"]:
        webbrowser.open(latest["confirmation_url"])
    elif action == "S" and latest["screenshot_path"]:
        path = Path(latest["screenshot_path"])
        if path.exists():
            webbrowser.open(path.resolve().as_uri())


def main() -> int:
    console = Console()
    database = Database()
    try:
        while True:
            rows = database.list_human_action_queue(True, ACTION_CENTRE_MAX_ITEMS)
            console.clear()
            console.print(Panel(f"{len(rows)} applications require human action.", title="VOCANTA Action Centre", border_style="bright_blue"))
            if rows:
                table = Table(expand=True)
                table.add_column("ID")
                table.add_column("Opportunity")
                table.add_column("Company")
                table.add_column("Role", ratio=3)
                table.add_column("Status")
                table.add_column("Visa")
                table.add_column("Email")
                for row in rows:
                    table.add_row(str(row["job_id"]), str(row["opportunity_score"]), row["company"], row["title"], row["status"], row["sponsorship_label"], row["email_status"] or "NONE")
                console.print(table)
            else:
                console.print("[green]No unresolved applications.[/green]")
            answer = Prompt.ask("Job ID, H history, or Enter to exit", default="", show_default=False).strip()
            if not answer:
                return 0
            if answer.upper() == "H":
                show_history(console, database)
                continue
            if not answer.isdigit():
                continue
            job_id = int(answer)
            row = next((item for item in rows if int(item["job_id"]) == job_id), None)
            if row is None:
                continue
            console.print(Panel(
                f"{row['company']}\n{row['title']}\n\nStatus: {row['status']}\nReason: {row['reason']}\n"
                f"Visa: {row['sponsorship_label']}\nRelocation: {row['relocation_label']}\n"
                f"Email: {row['email_status']} {row['email_location']}\nURL: {row['url']}",
                title=f"Job {job_id}",
            ))
            action = Prompt.ask("O open, E evidence, D done, S skip, Enter back", default="", show_default=False).strip().upper()
            if action == "O":
                webbrowser.open(row["url"])
            elif action == "E":
                evidence = list_submission_evidence(database.connection, job_id)
                if evidence:
                    path = Path(evidence[0]["evidence_path"])
                    if path.exists():
                        webbrowser.open(path.resolve().as_uri())
            elif action == "D":
                database.resolve_human_action(job_id, Prompt.ask("Resolution notes", default="Completed manually"))
            elif action == "S":
                database.resolve_human_action(job_id, Prompt.ask("Skip reason", default="Skipped after review"))
    finally:
        database.close()


if __name__ == "__main__":
    raise SystemExit(main())

from __future__ import annotations

import webbrowser
from pathlib import Path

from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt
from rich.table import Table

from core.database import Database
from core.submission_audit import list_submission_evidence


def main() -> int:
    console = Console()
    database = Database()
    try:
        while True:
            rows = database.connection.execute(
                """
                SELECT e.id, e.job_id, j.company, j.title, e.ats, e.outcome,
                       e.recorded_at, e.evidence_path, e.package_sha256,
                       e.confirmation_url, e.screenshot_path
                FROM submission_evidence AS e
                JOIN jobs AS j ON j.id = e.job_id
                ORDER BY e.recorded_at DESC, e.id DESC
                LIMIT 100
                """
            ).fetchall()
            console.clear()
            console.print(Panel(f"{len(rows)} recorded application executions.", title="VOCANTA Application History"))
            if not rows:
                console.print("No submission evidence recorded yet.")
                return 0
            table = Table(expand=True)
            table.add_column("Job")
            table.add_column("Company")
            table.add_column("Role", ratio=3)
            table.add_column("ATS")
            table.add_column("Outcome")
            table.add_column("Recorded")
            for row in rows:
                table.add_row(str(row["job_id"]), row["company"], row["title"], row["ats"], row["outcome"], row["recorded_at"][:19])
            console.print(table)
            answer = Prompt.ask("Job ID for evidence, or Enter to exit", default="", show_default=False).strip()
            if not answer:
                return 0
            if not answer.isdigit():
                continue
            evidence = list_submission_evidence(database.connection, int(answer))
            if not evidence:
                continue
            latest = evidence[0]
            console.print(Panel(
                f"Outcome: {latest['outcome']}\nATS: {latest['ats']}\nRecorded: {latest['recorded_at']}\n"
                f"Package SHA256: {latest['package_sha256']}\nEvidence: {latest['evidence_path']}\n"
                f"Confirmation: {latest['confirmation_url'] or 'None'}\nScreenshot: {latest['screenshot_path'] or 'None'}",
                title=f"Job {answer} Evidence",
            ))
            action = Prompt.ask("E evidence file, C confirmation, S screenshot, Enter back", default="", show_default=False).strip().upper()
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
    finally:
        database.close()


if __name__ == "__main__":
    raise SystemExit(main())

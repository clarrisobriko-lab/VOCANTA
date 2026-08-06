from rich.console import Console
from rich.table import Table

from core.database import Database


STATUS_STYLES = {
    "AUTO_SUBMITTED": "green",
    "READY_TO_REVIEW": "yellow",
    "HUMAN_VERIFICATION": "magenta",
    "FAILED": "red",
    "SKIPPED": "dim",
}


def main() -> int:
    console = Console()
    database = Database()
    try:
        rows = database.list_automation_attempts()
        table = Table(title="VOCANTA Automation Attempts", expand=True)
        table.add_column("Date")
        table.add_column("Company")
        table.add_column("Role", ratio=3)
        table.add_column("Status")
        table.add_column("Details", ratio=4)
        for row in rows:
            status = row["status"]
            style = STATUS_STYLES.get(status, "cyan")
            table.add_row(
                row["attempted_at"],
                row["company"],
                row["title"],
                f"[{style}]{status}[/]",
                row["message"],
            )
        console.print(table)
        return 0
    finally:
        database.close()


if __name__ == "__main__":
    raise SystemExit(main())

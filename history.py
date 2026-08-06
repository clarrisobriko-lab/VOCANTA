from rich.console import Console
from rich.table import Table

from core.database import Database


def main() -> int:
    console = Console()
    database = Database()
    try:
        raw_id = input("Enter job ID: ").strip()
        if not raw_id.isdigit():
            console.print("Invalid job ID.")
            return 1

        job_id = int(raw_id)
        job = database.get_job(job_id)
        if job is None:
            console.print("Job not found.")
            return 1

        rows = database.get_history(job_id)
        table = Table(title=f"History · {job['company']} · {job['title']}")
        table.add_column("Changed at")
        table.add_column("From")
        table.add_column("To")
        table.add_column("Notes")

        for row in rows:
            table.add_row(
                row["changed_at"],
                row["old_status"] or "",
                row["new_status"],
                row["notes"] or "",
            )
        console.print(table)
        return 0
    finally:
        database.close()


if __name__ == "__main__":
    raise SystemExit(main())

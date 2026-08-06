from rich.console import Console
from rich.table import Table

from core.database import Database


def main() -> int:
    console = Console()
    database = Database()
    try:
        database.refresh_employer_memory()
        rows = database.list_employer_memory()

        table = Table(title="VOCANTA Employer Memory", expand=True)
        table.add_column("Company")
        table.add_column("Applied", justify="right")
        table.add_column("Interviews", justify="right")
        table.add_column("Rejected", justify="right")
        table.add_column("Offers", justify="right")
        table.add_column("Automation", justify="right")
        table.add_column("Success", justify="right")
        table.add_column("Sponsor", justify="right")

        for row in rows:
            table.add_row(
                row["company"],
                str(row["applications"]),
                str(row["interviews"]),
                str(row["rejections"]),
                str(row["offers"]),
                str(row["automation_attempts"]),
                f"{row['automation_success_rate']}%",
                str(row["sponsorship_score"]),
            )
        console.print(table)
        return 0
    finally:
        database.close()


if __name__ == "__main__":
    raise SystemExit(main())

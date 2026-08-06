from rich.console import Console
from rich.table import Table

from config.settings import SHORTLIST_SCORE
from core.database import Database


def main() -> int:
    console = Console()
    database = Database()

    try:
        data = database.operational_statistics(SHORTLIST_SCORE)
        counts = data["status_counts"]

        summary = Table(title="VOCANTA Operational Statistics")
        summary.add_column("Metric")
        summary.add_column("Value", justify="right")

        for status in (
            "NEW",
            "SHORTLISTED",
            "PREPARING",
            "APPLIED",
            "FOLLOW_UP",
            "INTERVIEW",
            "REJECTED",
            "OFFER",
        ):
            summary.add_row(status, str(counts.get(status, 0)))

        summary.add_row("Average score", str(data["average_score"]))
        summary.add_row(
            "Applications this week",
            str(data["applications_this_week"]),
        )
        summary.add_row(
            "Interviews this month",
            str(data["interviews_this_month"]),
        )
        console.print(summary)

        companies = Table(title="Top Companies Applied To")
        companies.add_column("Company")
        companies.add_column("Applications", justify="right")
        for row in data["top_companies"]:
            companies.add_row(row["company"], str(row["count"]))
        console.print(companies)
        return 0
    finally:
        database.close()


if __name__ == "__main__":
    raise SystemExit(main())

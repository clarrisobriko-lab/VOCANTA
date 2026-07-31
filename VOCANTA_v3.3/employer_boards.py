from rich.console import Console
from rich.table import Table

from connectors.employer_registry import EmployerRegistry


def main() -> int:
    registry = EmployerRegistry()
    summary = registry.summary()
    console = Console()
    console.print(
        f"Greenhouse employer registry, configured {summary['configured']}, "
        f"approved {summary['approved']}, blocked {summary['blocked']}"
    )
    table = Table(title="VOCANTA Greenhouse Employer Boards", expand=True)
    table.add_column("Company")
    table.add_column("Board")
    table.add_column("Status")
    table.add_column("International")
    table.add_column("Sponsorship")
    table.add_column("Reason")
    for employer in registry.all_boards():
        table.add_row(
            employer.company,
            employer.board,
            "APPROVED" if employer.is_approved else "BLOCKED",
            employer.international_hiring.upper(),
            employer.sponsorship.upper(),
            employer.reason,
        )
    console.print(table)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

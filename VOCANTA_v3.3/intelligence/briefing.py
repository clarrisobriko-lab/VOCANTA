from rich.console import Console
from rich.panel import Panel
from rich.table import Table


def render_briefing(console: Console, data: dict[str, object]) -> None:
    summary = (
        f"[bold]New jobs:[/bold] {data['new_jobs']}   "
        f"[bold bright_green]Priority:[/bold bright_green] {data['priority_jobs']}   "
        f"[bold cyan]Apply:[/bold cyan] {data['apply_jobs']}   "
        f"[bold magenta]NGO:[/bold magenta] {data['ngo_jobs']}   "
        f"[bold green]Visa signals:[/bold green] {data['visa_jobs']}   "
        f"[bold red]Blocked:[/bold red] {data['blocked_jobs']}   "
        f"[bold yellow]Manual review:[/bold yellow] {data['manual_review']}"
    )
    console.print(
        Panel(
            summary,
            title="VOCANTA Daily Mission Briefing",
            border_style="bright_blue",
        )
    )

    targets = data.get("top_targets", [])
    if targets:
        table = Table(title="Recommended Targets", expand=True)
        table.add_column("Score", justify="right", width=5)
        table.add_column("Company")
        table.add_column("Role", ratio=4)
        table.add_column("Visa")
        table.add_column("Track")
        for row in targets:
            table.add_row(
                str(row["score"]),
                row["company"],
                row["title"],
                row["sponsorship_label"],
                row["recommendation"],
            )
        console.print(table)

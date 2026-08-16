from shutil import get_terminal_size

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from config.settings import APP_DISPLAY_NAME


def clip(value: str, width: int) -> str:
    text = " ".join((value or "").split())
    if len(text) <= width:
        return text
    return text[: max(1, width - 1)].rstrip() + "…"


def outcome_summary(outcomes: dict[str, int] | None) -> str:
    outcomes = outcomes or {}
    return (
        f"[bold green]Confirmed:[/bold green] {outcomes.get('applied', 0)}   "
        f"[bold yellow]Retry queue:[/bold yellow] {outcomes.get('retry_later', 0)}   "
        f"[bold red]Human action:[/bold red] {outcomes.get('human_required', 0)}   "
        f"[bold]Closed:[/bold] {outcomes.get('closed', 0)}   "
        f"[bold]Failed:[/bold] {outcomes.get('failed', 0)}"
    )


class Dashboard:
    def __init__(self) -> None:
        self.console = Console()

    def show(self, jobs, statistics: dict[str, int], connector_stats: dict[str, dict[str, int]], employer_stats: dict[str, object] | None = None, outcome_stats: dict[str, int] | None = None) -> None:
        width = get_terminal_size((120, 30)).columns
        pipeline = (
            f"[bold]Total:[/bold] {statistics['total']}   [bold]Relevant:[/bold] {statistics['relevant']}   "
            f"[bold]Shortlisted:[/bold] {statistics['shortlisted']}   [bold yellow]Applied:[/bold yellow] {statistics['applied']}   "
            f"[bold magenta]Follow ups:[/bold magenta] {statistics.get('follow_ups', 0)}   "
            f"[bold green]Interviews:[/bold green] {statistics.get('interviews', 0)}   "
            f"[bold bright_green]Offers:[/bold bright_green] {statistics.get('offers', 0)}"
        )
        self.console.print(Panel(pipeline, title=APP_DISPLAY_NAME, border_style="cyan"))

        if outcome_stats:
            self.console.print(Panel(outcome_summary(outcome_stats), title="Application Outcomes", border_style="blue"))

        if connector_stats:
            summary = ", ".join(f"{name}: {stats['accepted']}/{stats['fetched']}" for name, stats in sorted(connector_stats.items()))
            self.console.print(Panel(summary, title="Connector Results", border_style="dim"))

        if employer_stats:
            board_rows = employer_stats.get("boards", {})
            board_summary = ", ".join(f"{name}: {stats.get('admitted', 0)}/{stats.get('fetched', 0)}" for name, stats in sorted(board_rows.items())) or "No approved employer board returned candidates"
            policy_summary = f"Configured: {employer_stats.get('configured', 0)}   Approved: {employer_stats.get('approved', 0)}   Blocked: {employer_stats.get('blocked', 0)}\n{board_summary}"
            self.console.print(Panel(policy_summary, title="Greenhouse Employer Registry", border_style="green"))

        compact = width < 105
        table = Table(title="Ranked Job Matches", expand=True, show_lines=False)
        table.add_column("Score", justify="right", width=5, no_wrap=True)
        table.add_column("Company", ratio=2 if compact else 3, overflow="ellipsis", no_wrap=True)
        table.add_column("Title", ratio=5 if compact else 6, overflow="ellipsis", no_wrap=True)
        if not compact:
            table.add_column("Location", ratio=4, overflow="ellipsis", no_wrap=True)
        table.add_column("Visa", width=8, no_wrap=True)
        table.add_column("Track", width=9, no_wrap=True)
        table.add_column("Source", ratio=2, overflow="ellipsis", no_wrap=True)
        for job in jobs:
            row = [Text(str(job["score"]), justify="right"), clip(job["company"], 18 if compact else 24), clip(job["title"], 42 if compact else 56)]
            if not compact:
                row.append(clip(job["location"], 34))
            row.extend([job["sponsorship_label"], job["recommendation"], clip(job["source"], 16)])
            table.add_row(*row)
        self.console.print(table)

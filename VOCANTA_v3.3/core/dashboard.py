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


class Dashboard:
    def __init__(self) -> None:
        self.console = Console()

    def show(
        self,
        jobs,
        statistics: dict[str, int],
        connector_stats: dict[str, dict[str, int]],
        employer_stats: dict[str, object] | None = None,
    ) -> None:
        width = get_terminal_size((120, 30)).columns

        pipeline = (
            f"[bold]Total:[/bold] {statistics['total']}   "
            f"[bold]Relevant:[/bold] {statistics['relevant']}   "
            f"[bold]Shortlisted:[/bold] {statistics['shortlisted']}   "
            f"[bold yellow]Applied:[/bold yellow] {statistics['applied']}   "
            f"[bold magenta]Follow ups:[/bold magenta] "
            f"{statistics.get('follow_ups', 0)}   "
            f"[bold green]Interviews:[/bold green] "
            f"{statistics.get('interviews', 0)}   "
            f"[bold bright_green]Offers:[/bold bright_green] "
            f"{statistics.get('offers', 0)}"
        )
        self.console.print(
            Panel(
                pipeline,
                title=APP_DISPLAY_NAME,
                border_style="cyan",
            )
        )

        if connector_stats:
            summary = ", ".join(
                f"{name}: {stats['accepted']}/{stats['fetched']}"
                for name, stats in sorted(connector_stats.items())
            )
            self.console.print(
                Panel(
                    summary,
                    title="Connector Results",
                    border_style="dim",
                )
            )

        if employer_stats:
            board_rows = employer_stats.get("boards", {})
            board_summary = ", ".join(
                f"{name}: {stats.get('admitted', 0)}/{stats.get('fetched', 0)}"
                for name, stats in sorted(board_rows.items())
            ) or "No approved employer board returned candidates"
            policy_summary = (
                f"Configured: {employer_stats.get('configured', 0)}   "
                f"Approved: {employer_stats.get('approved', 0)}   "
                f"Blocked: {employer_stats.get('blocked', 0)}\n"
                f"{board_summary}"
            )
            self.console.print(
                Panel(
                    policy_summary,
                    title="Greenhouse Employer Registry",
                    border_style="green",
                )
            )

        compact = width < 105
        table = Table(
            title="Ranked Job Matches",
            expand=True,
            show_lines=False,
        )
        table.add_column("Score", justify="right", width=5, no_wrap=True)
        table.add_column(
            "Company",
            ratio=2 if compact else 3,
            overflow="ellipsis",
            no_wrap=True,
        )
        table.add_column(
            "Title",
            ratio=5 if compact else 6,
            overflow="ellipsis",
            no_wrap=True,
        )

        if not compact:
            table.add_column(
                "Location",
                ratio=4,
                overflow="ellipsis",
                no_wrap=True,
            )

        table.add_column("Visa", width=8, no_wrap=True)
        table.add_column("Track", width=9, no_wrap=True)
        table.add_column(
            "Source",
            ratio=2,
            overflow="ellipsis",
            no_wrap=True,
        )

        company_width = 18 if compact else 24
        title_width = 42 if compact else 56
        location_width = 34

        for job in jobs:
            row = [
                Text(str(job["score"]), justify="right"),
                clip(job["company"], company_width),
                clip(job["title"], title_width),
            ]

            if not compact:
                row.append(clip(job["location"], location_width))

            visa = job["sponsorship_label"]
            track = job["recommendation"]
            row.append(visa)
            row.append(track)
            row.append(clip(job["source"], 16))
            table.add_row(*row)

        self.console.print(table)

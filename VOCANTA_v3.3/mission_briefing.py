from rich.console import Console

from config.settings import SHORTLIST_SCORE
from core.database import Database
from intelligence.briefing import render_briefing


def main() -> int:
    console = Console()
    database = Database()
    try:
        database.refresh_employer_memory()
        render_briefing(console, database.mission_briefing(SHORTLIST_SCORE))
        return 0
    finally:
        database.close()


if __name__ == "__main__":
    raise SystemExit(main())

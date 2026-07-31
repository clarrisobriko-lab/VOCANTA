import logging
from collections.abc import Sequence

from connectors.base import BaseConnector
from connectors.employer_registry import EmployerBoard, EmployerRegistry
from connectors.http import create_session, get_json
from core.models import Job


logger = logging.getLogger(__name__)


class GreenhouseConnector(BaseConnector):
    """Employer-curated Greenhouse connector.

    Greenhouse itself is never treated as a monolithic source. Each approved
    employer board is fetched independently and carries its own policy metadata.
    """

    def __init__(self, registry: EmployerRegistry | None = None) -> None:
        self.registry = registry or EmployerRegistry()
        self.last_board_stats: dict[str, dict[str, int | str]] = {}

    @property
    def name(self) -> str:
        return "Greenhouse"

    @staticmethod
    def _matches_role_focus(title: str, board: EmployerBoard) -> bool:
        if not board.role_focus:
            return True
        normalized = " ".join((title or "").lower().split())
        return any(term in normalized for term in board.role_focus)

    def fetch_jobs(self) -> Sequence[Job]:
        session = create_session()
        jobs: list[Job] = []
        approved = self.registry.approved_boards()
        if not approved:
            logger.warning("No approved Greenhouse employer boards are configured")
            return jobs

        for employer in approved:
            url = f"https://boards-api.greenhouse.io/v1/boards/{employer.board}/jobs?content=true"
            fetched = 0
            admitted = 0
            try:
                payload = get_json(session, url)
            except Exception as exc:
                self.last_board_stats[employer.company] = {
                    "fetched": 0,
                    "admitted": 0,
                    "status": "FAILED",
                }
                logger.warning("Greenhouse board failed for %s, %s", employer.company, exc)
                continue

            raw_jobs = payload.get("jobs", [])
            if not isinstance(raw_jobs, list):
                logger.warning("Greenhouse board returned invalid jobs payload for %s", employer.company)
                continue

            for item in raw_jobs:
                fetched += 1
                title = str(item.get("title", "")).strip()
                if not self._matches_role_focus(title, employer):
                    continue
                location = (item.get("location") or {}).get("name", "")
                jobs.append(
                    Job(
                        company=employer.company,
                        title=title,
                        location=str(location).strip(),
                        source=f"Greenhouse:{employer.board}",
                        url=str(item.get("absolute_url", "")).strip(),
                        description=str(item.get("content", "") or ""),
                    )
                )
                admitted += 1

            self.last_board_stats[employer.company] = {
                "fetched": fetched,
                "admitted": admitted,
                "status": "OK",
            }
            logger.info(
                "Greenhouse employer board | %s | fetched %s | role-focus admitted %s",
                employer.company,
                fetched,
                admitted,
            )
        return jobs

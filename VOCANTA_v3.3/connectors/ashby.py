import logging
from collections.abc import Sequence

from config.settings import ASHBY_BOARDS
from connectors.base import BaseConnector
from connectors.http import create_session, get_json
from core.models import Job

logger = logging.getLogger(__name__)


class AshbyConnector(BaseConnector):
    @property
    def name(self) -> str:
        return "Ashby"

    def fetch_jobs(self) -> Sequence[Job]:
        session = create_session()
        jobs: list[Job] = []
        for company, board in ASHBY_BOARDS.items():
            url = f"https://api.ashbyhq.com/posting-api/job-board/{board}"
            try:
                payload = get_json(session, url)
            except Exception as exc:
                logger.warning("Ashby board failed for %s, %s", company, exc)
                continue
            for item in payload.get("jobs", []):
                location = str(item.get("location", "") or "")
                jobs.append(
                    Job(
                        company=company,
                        title=str(item.get("title", "")).strip(),
                        location=location.strip(),
                        source=self.name,
                        url=str(item.get("jobUrl", item.get("applyUrl", ""))).strip(),
                        description=str(item.get("descriptionPlain", "") or ""),
                        employment_type=str(item.get("employmentType", "") or ""),
                    )
                )
        return jobs

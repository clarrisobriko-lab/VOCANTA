import logging
from collections.abc import Sequence

from config.settings import ARBEITNOW_MAX_PAGES
from connectors.base import BaseConnector
from connectors.http import create_session, get_json
from core.models import Job

logger = logging.getLogger(__name__)


class ArbeitnowConnector(BaseConnector):
    @property
    def name(self) -> str:
        return "Arbeitnow"

    def fetch_jobs(self) -> Sequence[Job]:
        session = create_session()
        jobs: list[Job] = []

        for page in range(1, ARBEITNOW_MAX_PAGES + 1):
            url = f"https://www.arbeitnow.com/api/job-board-api?page={page}"
            try:
                payload = get_json(session, url)
            except Exception as exc:
                logger.warning("Arbeitnow page %s failed, %s", page, exc)
                break

            rows = payload.get("data", [])
            if not rows:
                break

            for item in rows:
                location = str(item.get("location", "")).strip()
                if item.get("remote"):
                    location = f"Remote, {location}" if location else "Remote"

                job_types = item.get("job_types") or []
                jobs.append(
                    Job(
                        company=str(item.get("company_name", "")).strip(),
                        title=str(item.get("title", "")).strip(),
                        location=location,
                        source=self.name,
                        url=str(item.get("url", "")).strip(),
                        description=str(item.get("description", "") or ""),
                        employment_type=", ".join(str(x) for x in job_types),
                    )
                )

            if not payload.get("links", {}).get("next"):
                break

        return jobs

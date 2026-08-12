import logging
from collections.abc import Sequence

from config.settings import WORKDAY_SITES
from connectors.base import BaseConnector
from connectors.http import create_session, get_json
from core.models import Job

logger = logging.getLogger(__name__)


class WorkdayConnector(BaseConnector):
    """Discover jobs from configured public Workday career sites.

    Configuration values are full Workday site roots, for example
    https://example.wd5.myworkdayjobs.com/External
    """

    @property
    def name(self) -> str:
        return "Workday"

    def fetch_jobs(self) -> Sequence[Job]:
        session = create_session()
        jobs: list[Job] = []
        for company, site_root in WORKDAY_SITES.items():
            root = str(site_root).rstrip("/")
            api_url = f"{root}/jobs"
            try:
                payload = get_json(session, api_url)
            except Exception as exc:
                logger.warning("Workday failed for %s, %s", company, exc)
                continue

            for item in payload.get("jobPostings", []):
                external_path = str(item.get("externalPath", "")).strip()
                if not external_path:
                    continue
                url = external_path if external_path.startswith("http") else f"{root}{external_path}"
                jobs.append(
                    Job(
                        company=company,
                        title=str(item.get("title", "")).strip(),
                        location=str(item.get("locationsText", "")).strip(),
                        source=self.name,
                        url=url,
                    )
                )
        return jobs

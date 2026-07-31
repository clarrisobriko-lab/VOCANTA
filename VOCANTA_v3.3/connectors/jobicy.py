import logging
from collections.abc import Sequence

from connectors.base import BaseConnector
from connectors.http import create_session, get_json
from core.models import Job

logger = logging.getLogger(__name__)


class JobicyConnector(BaseConnector):
    @property
    def name(self) -> str:
        return "Jobicy"

    def fetch_jobs(self) -> Sequence[Job]:
        session = create_session()
        url = "https://jobicy.com/api/v2/remote-jobs?count=50"
        try:
            payload = get_json(session, url)
        except Exception as exc:
            logger.warning("Jobicy failed, %s", exc)
            return []

        jobs: list[Job] = []
        for item in payload.get("jobs", []):
            jobs.append(
                Job(
                    company=str(item.get("companyName", "")).strip(),
                    title=str(item.get("jobTitle", "")).strip(),
                    location=str(item.get("jobGeo", "Remote") or "Remote").strip(),
                    source=self.name,
                    url=str(item.get("url", "")).strip(),
                    description=str(item.get("jobDescription", "") or ""),
                    salary=str(item.get("annualSalaryMin", "") or ""),
                    employment_type=str(item.get("jobType", "") or ""),
                )
            )
        return jobs

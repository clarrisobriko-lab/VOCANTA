import logging
from collections.abc import Sequence

from connectors.base import BaseConnector
from connectors.http import create_session, get_json
from core.models import Job

logger = logging.getLogger(__name__)


class RemotiveConnector(BaseConnector):
    @property
    def name(self) -> str:
        return "Remotive"

    def fetch_jobs(self) -> Sequence[Job]:
        session = create_session()
        url = "https://remotive.com/api/remote-jobs"
        try:
            payload = get_json(session, url)
        except Exception as exc:
            logger.warning("Remotive failed, %s", exc)
            return []

        jobs: list[Job] = []
        for item in payload.get("jobs", []):
            jobs.append(
                Job(
                    company=str(item.get("company_name", "")).strip(),
                    title=str(item.get("title", "")).strip(),
                    location=str(item.get("candidate_required_location", "Remote")).strip(),
                    source=self.name,
                    url=str(item.get("url", "")).strip(),
                    description=str(item.get("description", "") or ""),
                    salary=str(item.get("salary", "") or ""),
                    employment_type=str(item.get("job_type", "") or ""),
                )
            )
        return jobs

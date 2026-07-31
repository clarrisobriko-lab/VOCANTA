import logging
from collections.abc import Sequence

from config.settings import HIMALAYAS_MAX_PAGES
from connectors.base import BaseConnector
from connectors.http import create_session, get_json
from core.models import Job

logger = logging.getLogger(__name__)


class HimalayasConnector(BaseConnector):
    @property
    def name(self) -> str:
        return "Himalayas"

    def fetch_jobs(self) -> Sequence[Job]:
        session = create_session()
        jobs: list[Job] = []
        for page in range(HIMALAYAS_MAX_PAGES):
            offset = page * 20
            url = f"https://himalayas.app/jobs/api?limit=20&offset={offset}"
            try:
                payload = get_json(session, url)
            except Exception as exc:
                logger.warning("Himalayas page %s failed, %s", page + 1, exc)
                break

            rows = payload.get("jobs", []) if isinstance(payload, dict) else []
            if not rows:
                break
            for item in rows:
                company = item.get("company") or {}
                jobs.append(
                    Job(
                        company=str(company.get("name", item.get("companyName", ""))).strip(),
                        title=str(item.get("title", "")).strip(),
                        location=str(item.get("location", "Remote") or "Remote").strip(),
                        source=self.name,
                        url=str(item.get("applicationLink", item.get("url", ""))).strip(),
                        description=str(item.get("description", "") or ""),
                        employment_type=str(item.get("employmentType", "") or ""),
                    )
                )
            if len(rows) < 20:
                break
        return jobs

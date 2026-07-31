import logging
from collections.abc import Sequence

from config.settings import SMARTRECRUITERS_COMPANIES
from connectors.base import BaseConnector
from connectors.http import create_session, get_json
from core.models import Job

logger = logging.getLogger(__name__)


class SmartRecruitersConnector(BaseConnector):
    @property
    def name(self) -> str:
        return "SmartRecruiters"

    def fetch_jobs(self) -> Sequence[Job]:
        session = create_session()
        jobs: list[Job] = []
        for company, identifier in SMARTRECRUITERS_COMPANIES.items():
            url = f"https://api.smartrecruiters.com/v1/companies/{identifier}/postings?limit=100"
            try:
                payload = get_json(session, url)
            except Exception as exc:
                logger.warning("SmartRecruiters failed for %s, %s", company, exc)
                continue
            for item in payload.get("content", []):
                location_data = item.get("location") or {}
                location = ", ".join(
                    str(location_data.get(key, "")).strip()
                    for key in ("city", "region", "country")
                    if str(location_data.get(key, "")).strip()
                )
                jobs.append(
                    Job(
                        company=company,
                        title=str(item.get("name", "")).strip(),
                        location=location,
                        source=self.name,
                        url=str(item.get("ref", "")).strip(),
                        employment_type=str((item.get("typeOfEmployment") or {}).get("label", "")),
                    )
                )
        return jobs

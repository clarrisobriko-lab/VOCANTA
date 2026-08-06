import logging
from collections.abc import Sequence
from config.settings import LEVER_SITES
from connectors.base import BaseConnector
from connectors.http import create_session, get_json
from core.models import Job


logger = logging.getLogger(__name__)


class LeverConnector(BaseConnector):
    @property
    def name(self) -> str:
        return "Lever"

    def fetch_jobs(self) -> Sequence[Job]:
        session = create_session()
        jobs: list[Job] = []
        for company, site in LEVER_SITES.items():
            url = f"https://api.lever.co/v0/postings/{site}?mode=json"
            try:
                payload = get_json(session, url)
            except Exception as exc:
                logger.info("Lever site unavailable for %s, %s", company, exc)
                continue
            if not isinstance(payload, list):
                continue
            for item in payload:
                categories = item.get("categories") or {}
                description = " ".join(
                    part for part in [item.get("descriptionPlain", ""), item.get("additionalPlain", "")] if part
                )
                jobs.append(
                    Job(
                        company=company,
                        title=item.get("text", "").strip(),
                        location=str(categories.get("location", "")).strip(),
                        source=self.name,
                        url=item.get("hostedUrl", "").strip(),
                        description=description,
                        employment_type=str(categories.get("commitment", "")).strip(),
                    )
                )
        return jobs

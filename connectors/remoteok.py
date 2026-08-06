import logging
from collections.abc import Sequence

from config.settings import REMOTEOK_LIMIT
from connectors.base import BaseConnector
from connectors.http import create_session, get_json
from core.models import Job

logger = logging.getLogger(__name__)


class RemoteOKConnector(BaseConnector):
    @property
    def name(self) -> str:
        return "RemoteOK"

    def fetch_jobs(self) -> Sequence[Job]:
        session = create_session()
        try:
            payload = get_json(session, "https://remoteok.com/api")
        except Exception as exc:
            logger.warning("RemoteOK failed, %s", exc)
            return []

        jobs: list[Job] = []
        rows = payload[1:] if isinstance(payload, list) else []
        for item in rows[:REMOTEOK_LIMIT]:
            tags = item.get("tags") or []
            description = str(item.get("description", "") or "")
            if tags:
                description = f"{description} Tags: {', '.join(map(str, tags))}"
            jobs.append(
                Job(
                    company=str(item.get("company", "")).strip(),
                    title=str(item.get("position", "")).strip(),
                    location=str(item.get("location", "Remote") or "Remote").strip(),
                    source=self.name,
                    url=str(item.get("url", "")).strip(),
                    description=description,
                    salary=str(item.get("salary", "") or ""),
                )
            )
        return jobs

import logging
import re
from collections.abc import Sequence
from html import unescape
from urllib.parse import urljoin, urlparse

from connectors.base import BaseConnector
from connectors.http import create_session
from core.models import Job

logger = logging.getLogger(__name__)


class PublicHiddenSourceConnector(BaseConnector):
    """Conservative discovery connector for public hidden-job source pages.

    These sources are discovery-only. VOCANTA extracts only public outbound job
    links exposed in server-rendered HTML and routes applications to the
    employer/ATS URL. It does not bypass login, paywall, JavaScript, or access
    controls.
    """

    source_name = ""
    source_url = ""

    @property
    def name(self) -> str:
        return self.source_name

    def fetch_jobs(self) -> Sequence[Job]:
        try:
            session = create_session()
            response = session.get(self.source_url, timeout=12)
            response.raise_for_status()
        except Exception as exc:
            logger.warning("%s discovery failed, %s", self.name, exc)
            return []

        html = response.text or ""
        jobs: list[Job] = []
        seen: set[str] = set()
        pattern = re.compile(
            r'<a[^>]+href=["\'](?P<href>[^"\']+)["\'][^>]*>(?P<label>.*?)</a>',
            re.IGNORECASE | re.DOTALL,
        )
        source_host = (urlparse(self.source_url).hostname or "").lower()

        for match in pattern.finditer(html):
            href = unescape(match.group("href")).strip()
            label = re.sub(r"<[^>]+>", " ", match.group("label"))
            label = " ".join(unescape(label).split())
            url = urljoin(self.source_url, href)
            parsed = urlparse(url)
            host = (parsed.hostname or "").lower()
            if parsed.scheme not in {"http", "https"} or not host:
                continue
            if host == source_host or host.endswith("." + source_host):
                continue
            if url in seen or not label:
                continue
            seen.add(url)
            jobs.append(
                Job(
                    company=host.removeprefix("www."),
                    title=label[:240],
                    location="Remote" if "remote" in label.lower() else "",
                    source=self.name,
                    url=url,
                    description=f"Discovered via {self.name}; verify eligibility on employer site.",
                )
            )
        return jobs


class HiddenRolesConnector(PublicHiddenSourceConnector):
    source_name = "HiddenRoles"
    source_url = "https://hiddenroles.co/"


class UnlistedRemoteConnector(PublicHiddenSourceConnector):
    source_name = "UnlistedRemote"
    source_url = "https://unlistedremote.com/"

import logging
import re
from collections.abc import Sequence
from html import unescape
from urllib.parse import parse_qsl, urlencode, urljoin, urlparse, urlunparse

from connectors.base import BaseConnector
from connectors.http import create_session
from core.models import Job

logger = logging.getLogger(__name__)

TRACKING_KEYS = {"utm_source", "utm_medium", "utm_campaign", "utm_term", "utm_content", "ref", "source"}
BLOCKED_LABELS = {"privacy", "terms", "about", "contact", "login", "sign in", "sign up", "newsletter", "pricing"}
REMOTE_MARKERS = ("remote", "worldwide", "anywhere", "global")
AFRICA_MARKERS = ("africa", "emea", "worldwide", "anywhere", "global", "international")
RESTRICTED_MARKERS = (
    "us only", "u.s. only", "united states only", "canada only", "uk only",
    "united kingdom only", "eu only", "europe only", "must be located in",
    "must reside in", "work authorization required", "no sponsorship",
)
ATS_HOST_MARKERS = ("greenhouse.io", "greenhouse.com", "lever.co", "ashbyhq.com", "smartrecruiters.com", "workday.com", "myworkdayjobs.com")


def normalize_outbound_url(url: str) -> str:
    parsed = urlparse(url)
    query = [(k, v) for k, v in parse_qsl(parsed.query, keep_blank_values=True) if k.lower() not in TRACKING_KEYS]
    host = (parsed.hostname or "").lower().removeprefix("www.")
    netloc = host
    if parsed.port:
        netloc = f"{host}:{parsed.port}"
    return urlunparse((parsed.scheme.lower(), netloc, parsed.path.rstrip("/") or "/", "", urlencode(query), ""))


def source_quality(label: str, url: str) -> tuple[bool, str, str]:
    text = " ".join(label.lower().split())
    if len(text) < 4 or text in BLOCKED_LABELS:
        return False, "", "LOW"
    if any(marker in text for marker in RESTRICTED_MARKERS):
        return False, "", "RESTRICTED"
    location = "Remote" if any(marker in text for marker in REMOTE_MARKERS) else ""
    if any(marker in text for marker in AFRICA_MARKERS):
        location = "Remote, international"
    host = (urlparse(url).hostname or "").lower()
    reliability = "HIGH" if any(marker in host for marker in ATS_HOST_MARKERS) else "MEDIUM"
    return True, location, reliability


class PublicHiddenSourceConnector(BaseConnector):
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
        pattern = re.compile(r'<a[^>]+href=["\'](?P<href>[^"\']+)["\'][^>]*>(?P<label>.*?)</a>', re.IGNORECASE | re.DOTALL)
        source_host = (urlparse(self.source_url).hostname or "").lower().removeprefix("www.")

        for match in pattern.finditer(html):
            href = unescape(match.group("href")).strip()
            label = " ".join(unescape(re.sub(r"<[^>]+>", " ", match.group("label"))).split())
            raw_url = urljoin(self.source_url, href)
            parsed = urlparse(raw_url)
            host = (parsed.hostname or "").lower().removeprefix("www.")
            if parsed.scheme not in {"http", "https"} or not host or host == source_host or host.endswith("." + source_host):
                continue
            url = normalize_outbound_url(raw_url)
            allowed, location, reliability = source_quality(label, url)
            if not allowed or url in seen:
                continue
            seen.add(url)
            jobs.append(Job(
                company=host,
                title=label[:240],
                location=location,
                source=self.name,
                url=url,
                description=f"Discovered via {self.name}; source reliability {reliability}; verify final eligibility on employer site.",
            ))
        return jobs


class HiddenRolesConnector(PublicHiddenSourceConnector):
    source_name = "HiddenRoles"
    source_url = "https://hiddenroles.co/"


class UnlistedRemoteConnector(PublicHiddenSourceConnector):
    source_name = "UnlistedRemote"
    source_url = "https://unlistedremote.com/"

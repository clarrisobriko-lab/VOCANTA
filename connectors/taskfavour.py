from __future__ import annotations

import re
from urllib.parse import urljoin, urlparse

from bs4 import BeautifulSoup

from connectors.base import BaseConnector
from connectors.http import create_session
from core.models import Job


BASE_URL = "https://www.taskfavour.com"
REMOTE_URL = f"{BASE_URL}/jobs/category/remote"
_GLOBAL_MARKERS = ("worldwide", "anywhere", "global", "remote global", "work from anywhere")
_RESTRICTED_MARKERS = ("united states only", "us only", "usa only", "canada only", "uk only", "united kingdom only", "must be based in", "hybrid", "on-site", "onsite")
_ATS_HOSTS = ("greenhouse.io", "lever.co", "ashbyhq.com", "myworkdayjobs.com", "smartrecruiters.com")


def _text(node) -> str:
    return " ".join(node.get_text(" ", strip=True).split()) if node else ""


def _eligible_remote(text: str) -> bool:
    value = text.lower()
    if any(marker in value for marker in _RESTRICTED_MARKERS):
        return False
    return any(marker in value for marker in _GLOBAL_MARKERS) or "africa" in value or "nigeria" in value


def _best_application_url(card, listing_url: str) -> str:
    links = [urljoin(BASE_URL, a.get("href", "")) for a in card.select("a[href]")]
    for link in links:
        host = (urlparse(link).hostname or "").lower()
        if any(ats in host for ats in _ATS_HOSTS):
            return link
    return listing_url


class TaskFavourConnector(BaseConnector):
    """Guarded discovery connector. TaskFavour is a lead source, never authority.

    Only clearly global, Africa or Nigeria eligible remote listings are emitted.
    Employer ATS links are preferred when exposed by the source page.
    """

    @property
    def name(self) -> str:
        return "TaskFavour"

    def fetch_jobs(self):
        session = create_session()
        response = session.get(REMOTE_URL, timeout=20)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, "html.parser")
        jobs: list[Job] = []
        seen: set[str] = set()
        for card in soup.select("article, .job-card, [class*='job'], li"):
            text = _text(card)
            if len(text) < 20 or not _eligible_remote(text):
                continue
            anchor = card.select_one("a[href*='/job/'], a[href*='/jobs/']")
            if not anchor:
                continue
            listing_url = urljoin(BASE_URL, anchor.get("href", ""))
            if listing_url in seen:
                continue
            title = _text(card.select_one("h1,h2,h3,h4")) or _text(anchor)
            if not title:
                continue
            company_node = card.select_one("[class*='company'], [data-company]")
            company = _text(company_node) or "Unknown employer"
            location_match = re.search(r"(?:location|remote)\s*[:\-]?\s*([^|•]{2,80})", text, re.I)
            location = location_match.group(1).strip() if location_match else "Remote"
            url = _best_application_url(card, listing_url)
            jobs.append(Job(company=company, title=title, location=location, source=self.name, url=url, description=text[:5000]))
            seen.add(listing_url)
        return jobs

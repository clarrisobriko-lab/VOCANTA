from dataclasses import dataclass
from urllib.parse import urlparse

from automation.ats import adapter_for_url
from config.settings import (
    BLOCKED_AUTOMATION_DOMAINS,
    DISCOVERY_ONLY_AUTOMATION_DOMAINS,
)


@dataclass(frozen=True, slots=True)
class PreflightDecision:
    allowed: bool
    reason: str
    ats: str
    host: str


def _matches(host: str, domains: set[str]) -> str | None:
    for domain in domains:
        normalized = domain.lower().lstrip('.')
        if host == normalized or host.endswith('.' + normalized):
            return normalized
    return None


def assess_application_url(url: str) -> PreflightDecision:
    host = (urlparse(url).hostname or '').lower()
    if not host:
        return PreflightDecision(False, 'Application URL has no valid hostname', 'UNKNOWN', host)

    blocked = _matches(host, BLOCKED_AUTOMATION_DOMAINS)
    if blocked:
        return PreflightDecision(False, f'Blocked or Cloudflare-protected domain: {blocked}', 'BLOCKED', host)

    discovery_only = _matches(host, DISCOVERY_ONLY_AUTOMATION_DOMAINS)
    if discovery_only:
        return PreflightDecision(False, f'Discovery-only marketplace: {discovery_only}', 'DISCOVERY_ONLY', host)

    adapter = adapter_for_url(url)
    if not adapter.auto_submit_allowed:
        return PreflightDecision(
            False,
            f'Unsupported application platform for automatic submission: {adapter.name}',
            adapter.name,
            host,
        )

    return PreflightDecision(
        True,
        f'{adapter.name} application is ready for automation',
        adapter.name,
        host,
    )

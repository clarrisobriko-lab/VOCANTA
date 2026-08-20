from __future__ import annotations

from dataclasses import dataclass
from urllib.parse import urlsplit, urlunsplit

from automation.ats import adapter_for_url


@dataclass(frozen=True, slots=True)
class ControlledLiveTarget:
    employer: str
    title: str
    application_url: str
    allowed_ats: str
    max_submissions: int = 1


def canonical_url(url: str) -> str:
    parts = urlsplit(url.strip())
    return urlunsplit((parts.scheme.lower(), parts.netloc.lower(), parts.path.rstrip("/"), "", ""))


PERMITFLOW_ADMINISTRATIVE_ASSISTANT = ControlledLiveTarget(
    employer="PermitFlow",
    title="Administrative Assistant (International)",
    application_url="https://jobs.ashbyhq.com/permitflow/5b94082e-94f4-46ba-8e21-cfe238e8eae0/application",
    allowed_ats="ASHBY",
    max_submissions=1,
)


def authorize_target(url: str, target: ControlledLiveTarget = PERMITFLOW_ADMINISTRATIVE_ASSISTANT) -> None:
    if canonical_url(url) != canonical_url(target.application_url):
        raise RuntimeError("Live submission blocked: URL is not the authorized controlled-live target")
    ats = adapter_for_url(target.application_url).name.upper()
    if ats != target.allowed_ats:
        raise RuntimeError(f"Live submission blocked: expected {target.allowed_ats}, detected {ats}")
    if target.max_submissions != 1:
        raise RuntimeError("Live submission blocked: controlled-live target must permit exactly one submission")

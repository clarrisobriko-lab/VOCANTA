from dataclasses import dataclass
from urllib.parse import urlparse


STANDARD_CONFIRMATIONS = (
    "application submitted",
    "thank you for applying",
    "thanks for applying",
    "we have received your application",
    "application has been received",
    "your application was sent",
    "application complete",
)


@dataclass(frozen=True, slots=True)
class ATSAdapter:
    name: str
    host_markers: tuple[str, ...]
    final_submit_texts: tuple[str, ...]
    confirmation_phrases: tuple[str, ...]
    auto_submit_allowed: bool


ADAPTERS = (
    ATSAdapter(
        name="GREENHOUSE",
        host_markers=("greenhouse.io", "greenhouse.com"),
        final_submit_texts=("submit application", "submit"),
        confirmation_phrases=STANDARD_CONFIRMATIONS,
        auto_submit_allowed=True,
    ),
    ATSAdapter(
        name="LEVER",
        host_markers=("lever.co",),
        final_submit_texts=("submit application", "submit"),
        confirmation_phrases=STANDARD_CONFIRMATIONS,
        auto_submit_allowed=True,
    ),
    ATSAdapter(
        name="ASHBY",
        host_markers=("ashbyhq.com",),
        final_submit_texts=("submit application", "submit"),
        confirmation_phrases=STANDARD_CONFIRMATIONS + (
            "application received",
            "we'll be in touch",
        ),
        auto_submit_allowed=True,
    ),
    ATSAdapter(
        name="SMARTRECRUITERS",
        host_markers=("smartrecruiters.com",),
        final_submit_texts=("submit application", "send application"),
        confirmation_phrases=STANDARD_CONFIRMATIONS,
        auto_submit_allowed=False,
    ),
    ATSAdapter(
        name="WORKDAY",
        host_markers=("workday.com", "myworkdayjobs.com"),
        final_submit_texts=("submit",),
        confirmation_phrases=STANDARD_CONFIRMATIONS,
        auto_submit_allowed=False,
    ),
)


GENERIC_ADAPTER = ATSAdapter(
    name="GENERIC",
    host_markers=(),
    final_submit_texts=(
        "submit application",
        "send application",
        "complete application",
    ),
    confirmation_phrases=STANDARD_CONFIRMATIONS,
    auto_submit_allowed=False,
)


def adapter_for_url(url: str) -> ATSAdapter:
    host = urlparse(url).netloc.lower()
    for adapter in ADAPTERS:
        if any(marker in host for marker in adapter.host_markers):
            return adapter
    return GENERIC_ADAPTER

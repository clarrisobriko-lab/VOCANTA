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
    ATSAdapter("GREENHOUSE", ("greenhouse.io", "greenhouse.com"), ("submit application", "submit"), STANDARD_CONFIRMATIONS, True),
    ATSAdapter("LEVER", ("lever.co",), ("submit application", "submit"), STANDARD_CONFIRMATIONS, True),
    ATSAdapter("ASHBY", ("ashbyhq.com",), ("submit application", "submit"), STANDARD_CONFIRMATIONS + ("application received", "we'll be in touch"), False),
    ATSAdapter(
        "SMARTRECRUITERS",
        ("smartrecruiters.com",),
        ("submit application", "send application", "apply"),
        STANDARD_CONFIRMATIONS + ("application successfully submitted", "your application has been submitted"),
        False,
    ),
    ATSAdapter(
        "WORKDAY",
        ("workday.com", "myworkdayjobs.com"),
        ("submit", "submit application"),
        STANDARD_CONFIRMATIONS + ("your application was submitted", "your application has been submitted"),
        False,
    ),
)


GENERIC_ADAPTER = ATSAdapter(
    name="GENERIC",
    host_markers=(),
    final_submit_texts=("submit application", "send application", "complete application"),
    confirmation_phrases=STANDARD_CONFIRMATIONS,
    auto_submit_allowed=False,
)


def adapter_for_url(url: str) -> ATSAdapter:
    host = urlparse(url).netloc.lower()
    for adapter in ADAPTERS:
        if any(marker in host for marker in adapter.host_markers):
            return adapter
    return GENERIC_ADAPTER

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum


class LiveOutcome(str, Enum):
    READY = "READY"
    SUBMITTED = "SUBMITTED"
    UNKNOWN = "UNKNOWN"
    HUMAN_REQUIRED = "HUMAN_REQUIRED"
    FAILED = "FAILED"


@dataclass(frozen=True, slots=True)
class LiveExecutionRecord:
    employer: str
    role: str
    target_url: str
    ats: str
    outcome: LiveOutcome
    attempted_at: str
    confirmation_evidence: str = ""
    application_id: str = ""
    message: str = ""

    @property
    def confirmed(self) -> bool:
        return self.outcome == LiveOutcome.SUBMITTED and bool(self.confirmation_evidence.strip())


def new_record(*, employer: str, role: str, target_url: str, ats: str, outcome: LiveOutcome,
               confirmation_evidence: str = "", application_id: str = "", message: str = "",
               now: datetime | None = None) -> LiveExecutionRecord:
    if outcome == LiveOutcome.SUBMITTED and not confirmation_evidence.strip():
        raise ValueError("SUBMITTED requires recognized confirmation evidence")
    if not employer.strip() or not role.strip() or not target_url.strip() or not ats.strip():
        raise ValueError("employer, role, target_url and ats are required")
    stamp = (now or datetime.now(timezone.utc)).astimezone(timezone.utc).isoformat()
    return LiveExecutionRecord(employer.strip(), role.strip(), target_url.strip(), ats.strip(), outcome,
                               stamp, confirmation_evidence.strip(), application_id.strip(), message.strip())


def should_retry(record: LiveExecutionRecord) -> bool:
    """A live attempt is never automatically retried after an ambiguous or confirmed outcome."""
    return record.outcome == LiveOutcome.FAILED

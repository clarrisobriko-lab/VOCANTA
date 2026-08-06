from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from agents.filters import JobFilter
from agents.matcher import Matcher
from agents.scorer import Scorer
from core.models import Job
from intelligence.assessment import assess_job


class RejectionReason(StrEnum):
    DUPLICATE = "duplicate"
    INVALID = "invalid"
    LOCATION = "unsupported_location"
    ROLE = "irrelevant_role"
    SCORE = "below_minimum_score"


@dataclass(frozen=True, slots=True)
class DiscoveryResult:
    job: Job | None
    intelligence: object | None = None
    rejection_reason: RejectionReason | None = None

    @property
    def accepted(self) -> bool:
        return self.job is not None and self.rejection_reason is None


class DiscoveryEngine:
    """Deterministic production gate for every discovered vacancy."""

    def __init__(
        self,
        minimum_score: int,
        job_filter: JobFilter | None = None,
        matcher: Matcher | None = None,
        scorer: Scorer | None = None,
    ) -> None:
        if not 0 <= minimum_score <= 100:
            raise ValueError("minimum_score must be between 0 and 100")
        self.minimum_score = minimum_score
        self.job_filter = job_filter or JobFilter()
        self.matcher = matcher or Matcher()
        self.scorer = scorer or Scorer()

    def evaluate(self, job: Job, seen_urls: set[str]) -> DiscoveryResult:
        if not job.is_valid:
            return DiscoveryResult(None, rejection_reason=RejectionReason.INVALID)
        if not self.job_filter.has_unique_url(job, seen_urls):
            return DiscoveryResult(None, rejection_reason=RejectionReason.DUPLICATE)
        if not self.job_filter.has_supported_location(job):
            return DiscoveryResult(None, rejection_reason=RejectionReason.LOCATION)
        if not self.matcher.is_relevant(job):
            return DiscoveryResult(None, rejection_reason=RejectionReason.ROLE)

        scored_job = job.with_score(self.scorer.score(job))
        if scored_job.score < self.minimum_score:
            return DiscoveryResult(None, rejection_reason=RejectionReason.SCORE)
        return DiscoveryResult(scored_job, intelligence=assess_job(scored_job))

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable


@dataclass(frozen=True)
class PortfolioJob:
    title: str
    url: str
    category: str = ""
    location: str = ""
    remote_global: bool = False


@dataclass(frozen=True)
class TargetingPolicy:
    preferred_categories: tuple[str, ...] = (
        "legal", "legal operations", "compliance", "operations", "administration",
        "human resources", "hr", "recruitment", "customer success", "support",
    )
    excluded_categories: tuple[str, ...] = (
        "engineering", "infrastructure", "devops", "cloud", "cybersecurity", "data",
    )
    excluded_title_terms: tuple[str, ...] = (
        "engineer", "developer", "devops", "data scientist", "security engineer",
    )


def _norm(value: str) -> str:
    return " ".join((value or "").casefold().split())


def eligible(job: PortfolioJob, policy: TargetingPolicy) -> bool:
    title = _norm(job.title)
    category = _norm(job.category)
    if any(term in title for term in policy.excluded_title_terms):
        return False
    if any(term in category for term in policy.excluded_categories):
        return False
    return True


def score(job: PortfolioJob, policy: TargetingPolicy) -> int:
    if not eligible(job, policy):
        return -10_000
    haystack = f"{_norm(job.title)} {_norm(job.category)}"
    points = 0
    for index, category in enumerate(policy.preferred_categories):
        if category in haystack:
            points += max(10, 100 - index * 8)
    if job.remote_global:
        points += 25
    if "legal" in haystack or "compliance" in haystack:
        points += 35
    if "operations" in haystack or "administration" in haystack:
        points += 25
    return points


def select_target(jobs: Iterable[PortfolioJob], policy: TargetingPolicy | None = None) -> PortfolioJob | None:
    policy = policy or TargetingPolicy()
    candidates = [job for job in jobs if eligible(job, policy)]
    if not candidates:
        return None
    return max(candidates, key=lambda job: (score(job, policy), _norm(job.title), job.url))

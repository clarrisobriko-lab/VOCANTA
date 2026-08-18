from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Iterable

from automation.portfolio_targeting import PortfolioJob, TargetingPolicy, eligible, score


class DryRunStatus(str, Enum):
    READY = "READY"
    NO_ELIGIBLE_TARGET = "NO_ELIGIBLE_TARGET"
    EVIDENCE_GAP = "EVIDENCE_GAP"
    UNSAFE_WORKFLOW = "UNSAFE_WORKFLOW"


@dataclass(frozen=True, slots=True)
class CandidateEvidence:
    skills: frozenset[str]
    approved_documents: frozenset[str]


@dataclass(frozen=True, slots=True)
class EmployerVacancy:
    job: PortfolioJob
    required_skills: frozenset[str] = frozenset()
    required_documents: frozenset[str] = frozenset({"cv"})
    asks_for_payment: bool = False
    asks_for_financial_information: bool = False


@dataclass(frozen=True, slots=True)
class DryRunResult:
    employer: str
    status: DryRunStatus
    selected: EmployerVacancy | None
    missing_skills: tuple[str, ...] = ()
    missing_documents: tuple[str, ...] = ()
    reason: str = ""


def _norm_set(values: Iterable[str]) -> set[str]:
    return {" ".join(v.casefold().split()) for v in values if v and v.strip()}


def run_employer_dry_run(*, employer: str, vacancies: Iterable[EmployerVacancy],
                         evidence: CandidateEvidence,
                         policy: TargetingPolicy | None = None) -> DryRunResult:
    policy = policy or TargetingPolicy()
    candidates = [v for v in vacancies if eligible(v.job, policy)]
    if not candidates:
        return DryRunResult(employer, DryRunStatus.NO_ELIGIBLE_TARGET, None,
                            reason="No vacancy passed portfolio eligibility policy")

    candidates.sort(key=lambda v: (score(v.job, policy), v.job.title.casefold(), v.job.url), reverse=True)
    skills = _norm_set(evidence.skills)
    documents = _norm_set(evidence.approved_documents)

    for vacancy in candidates:
        if vacancy.asks_for_payment or vacancy.asks_for_financial_information:
            continue
        missing_skills = sorted(_norm_set(vacancy.required_skills) - skills)
        missing_documents = sorted(_norm_set(vacancy.required_documents) - documents)
        if not missing_skills and not missing_documents:
            return DryRunResult(employer, DryRunStatus.READY, vacancy)

    safe = [v for v in candidates if not v.asks_for_payment and not v.asks_for_financial_information]
    if not safe:
        return DryRunResult(employer, DryRunStatus.UNSAFE_WORKFLOW, None,
                            reason="All eligible workflows request prohibited payment or financial information")

    best = safe[0]
    return DryRunResult(
        employer,
        DryRunStatus.EVIDENCE_GAP,
        best,
        tuple(sorted(_norm_set(best.required_skills) - skills)),
        tuple(sorted(_norm_set(best.required_documents) - documents)),
        "Highest ranked safe vacancy is missing approved candidate evidence",
    )

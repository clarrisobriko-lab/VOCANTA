from __future__ import annotations

from dataclasses import dataclass

from automation.claims_ledger import evidence_for
from automation.tailoring import extract_keywords
from core.models import Job


@dataclass(frozen=True, slots=True)
class RequirementEvidence:
    requirement: str
    evidence: tuple[str, ...]
    supported: bool


@dataclass(frozen=True, slots=True)
class EvidenceManifest:
    requirements: tuple[RequirementEvidence, ...]
    precision: float
    coverage: float

    @property
    def supported(self) -> tuple[RequirementEvidence, ...]:
        return tuple(item for item in self.requirements if item.supported)

    @property
    def unsupported(self) -> tuple[RequirementEvidence, ...]:
        return tuple(item for item in self.requirements if not item.supported)


def build_evidence_manifest(job: Job) -> EvidenceManifest:
    required = extract_keywords(job)
    rows = tuple(
        RequirementEvidence(requirement=skill, evidence=evidence_for(skill), supported=bool(evidence_for(skill)))
        for skill in required
    )
    supported = sum(item.supported for item in rows)
    coverage = 1.0 if not rows else supported / len(rows)
    selected = tuple(item for item in rows if item.supported)
    precision = 1.0 if not selected else sum(bool(item.evidence) for item in selected) / len(selected)
    return EvidenceManifest(requirements=rows, precision=precision, coverage=coverage)


def grounded_keywords(job: Job) -> tuple[str, ...]:
    return tuple(item.requirement for item in build_evidence_manifest(job).supported)

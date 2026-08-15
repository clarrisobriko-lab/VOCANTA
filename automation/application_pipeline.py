from dataclasses import dataclass, replace

from agents.scorer import ApplicationDecision, Scorer
from automation.browser import AutomationResult
from automation.hardened_browser import HardenedBrowserApplicationEngine
from automation.package_builder import ApplicationPackage, build_application_package
from automation.profile import ApplicantProfile
from automation.tailoring import TailoredDocuments, tailor_documents
from core.models import Job


@dataclass(frozen=True, slots=True)
class PipelineResult:
    decision: ApplicationDecision
    documents: TailoredDocuments | None
    package: ApplicationPackage | None
    automation: AutomationResult | None


def profile_for_package(profile: ApplicantProfile, package: ApplicationPackage) -> ApplicantProfile:
    """Point browser uploads at employer-facing PDFs only."""
    supporting = str(package.supporting_documents[0]) if package.supporting_documents else ""
    return replace(
        profile,
        resume_path=str(package.cv_pdf),
        cover_letter_path=str(package.cover_letter_pdf),
        supporting_document_path=supporting,
    )


def run_application_pipeline(
    job: Job,
    job_id: int,
    profile: ApplicantProfile,
    *,
    scorer: Scorer | None = None,
    browser_engine_factory=HardenedBrowserApplicationEngine,
) -> PipelineResult:
    """Score, tailor, package and submit one eligible vacancy."""
    decision = (scorer or Scorer()).evaluate(job)
    if not decision.should_apply:
        return PipelineResult(decision, None, None, None)

    documents = tailor_documents(job, job_id, profile)
    package = build_application_package(job, documents, decision)
    browser_profile = profile_for_package(profile, package)
    automation = browser_engine_factory(browser_profile).apply(job.url, job_id)
    return PipelineResult(decision, documents, package, automation)

from dataclasses import dataclass, replace
import time

from agents.scorer import ApplicationDecision, Scorer
from automation.browser import AutomationResult
from automation.hardened_browser import HardenedBrowserApplicationEngine
from automation.package_builder import ApplicationPackage, build_application_package
from automation.profile import ApplicantProfile
from automation.recovery import RecoveryAction, decide_recovery
from automation.tailoring import TailoredDocuments, tailor_documents
from automation.upload_hardening import validate_upload_path
from core.models import Job


@dataclass(frozen=True, slots=True)
class PipelineResult:
    decision: ApplicationDecision
    documents: TailoredDocuments | None
    package: ApplicationPackage | None
    automation: AutomationResult | None


def profile_for_package(profile: ApplicantProfile, package: ApplicationPackage) -> ApplicantProfile:
    supporting = str(package.supporting_documents[0]) if package.supporting_documents else ""
    return replace(profile, resume_path=str(package.cv_pdf), cover_letter_path=str(package.cover_letter_pdf), supporting_document_path=supporting)


def validate_browser_documents(profile: ApplicantProfile) -> None:
    required = (("CV", profile.resume_path), ("cover letter", profile.cover_letter_path))
    for label, path in required:
        valid, reason = validate_upload_path(path)
        if not valid: raise RuntimeError(f"Invalid {label} upload: {reason}")
    if profile.supporting_document_path:
        valid, reason = validate_upload_path(profile.supporting_document_path)
        if not valid: raise RuntimeError(f"Invalid supporting document upload: {reason}")


def _apply_with_recovery(job: Job, job_id: int, profile: ApplicantProfile, browser_engine_factory, *, max_attempts: int = 3, sleep_fn=time.sleep) -> AutomationResult:
    last: AutomationResult | None = None
    for attempt in range(1, max_attempts + 1):
        try:
            last = browser_engine_factory(profile).apply(job.url, job_id)
        except Exception as exc:
            decision = decide_recovery(str(exc), attempt, max_attempts)
        else:
            if last.status in {"SUBMITTED", "SUCCESS"}:
                return last
            decision = decide_recovery(f"{last.status} {last.message}", attempt, max_attempts)
        if decision.action == RecoveryAction.RETRY:
            sleep_fn(decision.delay_seconds)
            continue
        if decision.action == RecoveryAction.REQUEUE:
            return last or AutomationResult("REQUEUE", decision.reason, "", 0)
        if decision.action == RecoveryAction.HUMAN_REQUIRED:
            return last or AutomationResult("HUMAN_REQUIRED", decision.reason, "", 0)
        return last or AutomationResult("FAILED", decision.reason, "", 0)
    return last or AutomationResult("FAILED", "application retry budget exhausted", "", 0)


def run_application_pipeline(job: Job, job_id: int, profile: ApplicantProfile, *, scorer: Scorer | None = None, browser_engine_factory=HardenedBrowserApplicationEngine) -> PipelineResult:
    decision = (scorer or Scorer()).evaluate(job)
    if not decision.should_apply: return PipelineResult(decision, None, None, None)
    documents = tailor_documents(job, job_id, profile)
    package = build_application_package(job, documents, decision)
    browser_profile = profile_for_package(profile, package)
    validate_browser_documents(browser_profile)
    automation = _apply_with_recovery(job, job_id, browser_profile, browser_engine_factory)
    return PipelineResult(decision, documents, package, automation)

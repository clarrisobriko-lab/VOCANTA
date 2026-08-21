from dataclasses import dataclass, replace
from pathlib import Path
import time

from agents.scorer import ApplicationDecision, Scorer
from automation.browser import AutomationResult
from automation.hardened_browser import HardenedBrowserApplicationEngine
from automation.package_builder import ApplicationPackage, build_application_package
from automation.profile import ApplicantProfile
from automation.recovery import RecoveryAction, decide_recovery
from automation.submission_evidence import build_submission_evidence, persist_submission_evidence
from automation.tailoring import TailoredDocuments, tailor_documents
from automation.upload_hardening import validate_upload_path
from core.models import Job
from core.submission_audit import record_submission_evidence


@dataclass(frozen=True, slots=True)
class PipelineResult:
    decision: ApplicationDecision
    documents: TailoredDocuments | None
    package: ApplicationPackage | None
    automation: AutomationResult | None
    evidence_path: Path | None = None


def profile_for_package(profile: ApplicantProfile, package: ApplicationPackage) -> ApplicantProfile:
    supporting = str(package.supporting_documents[0]) if package.supporting_documents else ""
    return replace(profile, resume_path=str(package.cv_pdf), cover_letter_path=str(package.cover_letter_pdf), supporting_document_path=supporting)


def validate_browser_documents(profile: ApplicantProfile) -> None:
    required = (("CV", profile.resume_path), ("cover letter", profile.cover_letter_path))
    for label, path in required:
        valid, reason = validate_upload_path(path)
        if not valid:
            raise RuntimeError(f"Invalid {label} upload: {reason}")
    if profile.supporting_document_path:
        valid, reason = validate_upload_path(profile.supporting_document_path)
        if not valid:
            raise RuntimeError(f"Invalid supporting document upload: {reason}")


_CONFIRMED_STATUSES = {"SUBMITTED", "SUCCESS", "AUTO_SUBMITTED", "CONFIRMED"}
_AMBIGUOUS_STATUSES = {"UNKNOWN", "SUBMISSION_UNVERIFIED"}
_HUMAN_STATUSES = {"HUMAN_REQUIRED", "HUMAN_VERIFICATION", "MANUAL_REQUIRED", "READY_TO_REVIEW"}
_TERMINAL_STATUSES = {"SKIPPED_SOURCE", "FAILED"}


def _apply_with_recovery(job: Job, job_id: int, profile: ApplicantProfile, browser_engine_factory, *, max_attempts: int = 3, sleep_fn=time.sleep) -> AutomationResult:
    """Apply with a bounded retry budget.

    A result that indicates a submit click may already have occurred is never retried.
    This prevents duplicate employer applications when confirmation evidence is absent.
    """
    last: AutomationResult | None = None
    for attempt in range(1, max_attempts + 1):
        try:
            last = browser_engine_factory(profile).apply(job.url, job_id)
        except Exception as exc:
            decision = decide_recovery(str(exc), attempt, max_attempts)
        else:
            status = (last.status or "").upper()
            if status in _CONFIRMED_STATUSES:
                return last
            if status in _AMBIGUOUS_STATUSES:
                return last
            if status in _HUMAN_STATUSES or status == "SKIPPED_SOURCE":
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


def _persist_pipeline_evidence(job: Job, job_id: int, package: ApplicationPackage, automation: AutomationResult, *, database=None, application_run_id: int | None = None) -> Path:
    confirmation_url = getattr(automation, "confirmation_url", "") or ""
    screenshot_path = getattr(automation, "screenshot", "") or ""
    evidence = build_submission_evidence(
        job,
        job_id,
        package,
        outcome=automation.status,
        message=automation.message,
        confirmation_url=confirmation_url,
        screenshot_path=screenshot_path,
    )
    path = persist_submission_evidence(evidence, package.folder / "submission_evidence")
    if database is not None:
        connection = getattr(database, "connection", database)
        record_submission_evidence(
            connection,
            job_id=job_id,
            application_run_id=application_run_id,
            evidence_path=path,
            package_sha256=evidence.package_sha256,
            ats=evidence.ats,
            outcome=evidence.outcome,
            confirmation_url=evidence.confirmation_url,
            screenshot_path=evidence.screenshot_path,
        )
        connection.commit()
    return path


def run_application_pipeline(job: Job, job_id: int, profile: ApplicantProfile, *, scorer: Scorer | None = None, browser_engine_factory=HardenedBrowserApplicationEngine, database=None, application_run_id: int | None = None) -> PipelineResult:
    decision = (scorer or Scorer()).evaluate(job)
    if not decision.should_apply:
        return PipelineResult(decision, None, None, None, None)
    documents = tailor_documents(job, job_id, profile)
    package = build_application_package(job, documents, decision)
    browser_profile = profile_for_package(profile, package)
    validate_browser_documents(browser_profile)
    automation = _apply_with_recovery(job, job_id, browser_profile, browser_engine_factory)
    evidence_path = _persist_pipeline_evidence(job, job_id, package, automation, database=database, application_run_id=application_run_id)
    return PipelineResult(decision, documents, package, automation, evidence_path)

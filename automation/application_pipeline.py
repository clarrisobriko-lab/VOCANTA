from dataclasses import dataclass, is_dataclass, replace
from pathlib import Path
from types import SimpleNamespace
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


def profile_for_package(profile, package):
    supporting = str(package.supporting_documents[0]) if package.supporting_documents else ""
    updates = {
        "resume_path": str(package.cv_pdf),
        "cover_letter_path": str(package.cover_letter_pdf),
        "supporting_document_path": supporting,
    }
    if is_dataclass(profile) and not isinstance(profile, type):
        return replace(profile, **updates)
    values = dict(vars(profile)) if hasattr(profile, "__dict__") else {}
    values.update(updates)
    return SimpleNamespace(**values)


def validate_browser_documents(profile):
    for label, path in (("CV", profile.resume_path), ("cover letter", profile.cover_letter_path)):
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


def _engine(factory, profile, job_context):
    try:
        return factory(profile, job_context=job_context)
    except TypeError:
        return factory(profile)


def _apply_with_recovery(job, job_id, profile, browser_engine_factory, *, max_attempts=3, sleep_fn=time.sleep):
    last = None
    title = getattr(job, "title", "") or ""
    description = getattr(job, "description", "") or ""
    job_context = "\n".join(x for x in (title, description) if x)
    for attempt in range(1, max_attempts + 1):
        try:
            last = _engine(browser_engine_factory, profile, job_context).apply(job.url, job_id)
        except Exception as exc:
            decision = decide_recovery(str(exc), attempt, max_attempts)
        else:
            status = (last.status or "").upper()
            if status in _CONFIRMED_STATUSES or status in _AMBIGUOUS_STATUSES or status in _HUMAN_STATUSES or status == "SKIPPED_SOURCE":
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


def _persist_pipeline_evidence(job, job_id, package, automation, *, database=None, application_run_id=None):
    evidence = build_submission_evidence(job, job_id, package, outcome=automation.status, message=automation.message, confirmation_url=getattr(automation, "confirmation_url", "") or "", screenshot_path=getattr(automation, "screenshot", "") or "")
    path = persist_submission_evidence(evidence, package.folder / "submission_evidence")
    if database is not None:
        connection = getattr(database, "connection", database)
        record_submission_evidence(connection, job_id=job_id, application_run_id=application_run_id, evidence_path=path, package_sha256=evidence.package_sha256, ats=evidence.ats, outcome=evidence.outcome, confirmation_url=evidence.confirmation_url, screenshot_path=evidence.screenshot_path)
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

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path

from automation.ats import adapter_for_url
from automation.package_builder import ApplicationPackage
from core.models import Job


@dataclass(frozen=True, slots=True)
class SubmissionEvidence:
    job_id: int
    company: str
    title: str
    job_url: str
    ats: str
    outcome: str
    message: str
    confirmation_url: str
    screenshot_path: str
    attempted_at: str
    cv_path: str
    cover_letter_path: str
    package_archive: str
    package_sha256: str


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def build_submission_evidence(
    job: Job,
    job_id: int,
    package: ApplicationPackage,
    *,
    outcome: str,
    message: str = "",
    confirmation_url: str = "",
    screenshot_path: str = "",
    attempted_at: str | None = None,
) -> SubmissionEvidence:
    return SubmissionEvidence(
        job_id=job_id,
        company=job.company,
        title=job.title,
        job_url=job.url,
        ats=adapter_for_url(job.url).name,
        outcome=outcome.strip().upper(),
        message=message.strip(),
        confirmation_url=confirmation_url.strip(),
        screenshot_path=screenshot_path.strip(),
        attempted_at=attempted_at or datetime.now(timezone.utc).isoformat(),
        cv_path=str(package.cv_pdf),
        cover_letter_path=str(package.cover_letter_pdf),
        package_archive=str(package.archive),
        package_sha256=_sha256(package.archive),
    )


def persist_submission_evidence(evidence: SubmissionEvidence, directory: Path | str) -> Path:
    target_dir = Path(directory)
    target_dir.mkdir(parents=True, exist_ok=True)
    stamp = evidence.attempted_at.replace(":", "").replace("+", "_").replace(".", "_")
    target = target_dir / f"job_{evidence.job_id}_{stamp}.json"
    payload = json.dumps(asdict(evidence), indent=2, sort_keys=True)
    target.write_text(payload + "\n", encoding="utf-8")
    return target

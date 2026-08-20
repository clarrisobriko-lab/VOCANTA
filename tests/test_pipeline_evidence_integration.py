from pathlib import Path
from types import SimpleNamespace

from automation.application_pipeline import _persist_pipeline_evidence
from core.models import Job


def test_pipeline_persists_execution_evidence_next_to_package(tmp_path):
    folder = tmp_path / "application_package"
    folder.mkdir()
    cv = folder / "cv.pdf"
    cover = folder / "cover.pdf"
    archive = tmp_path / "package.zip"
    cv.write_bytes(b"cv")
    cover.write_bytes(b"cover")
    archive.write_bytes(b"package")
    package = SimpleNamespace(folder=folder, cv_pdf=cv, cover_letter_pdf=cover, archive=archive)
    automation = SimpleNamespace(
        status="SUBMITTED",
        message="Application successfully submitted",
        active_url="https://jobs.lever.co/acme/123/thanks",
        screenshot_path="screenshots/123.png",
    )
    job = Job(company="Acme", title="Executive Assistant", location="Remote", source="Lever", url="https://jobs.lever.co/acme/123", description="")

    evidence_path = _persist_pipeline_evidence(job, 42, package, automation)

    assert isinstance(evidence_path, Path)
    assert evidence_path.exists()
    assert evidence_path.parent == folder / "submission_evidence"
    text = evidence_path.read_text(encoding="utf-8")
    assert '"outcome": "SUBMITTED"' in text
    assert '"ats": "LEVER"' in text
    assert '"job_id": 42' in text

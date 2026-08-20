import json
from types import SimpleNamespace

from automation.submission_evidence import build_submission_evidence, persist_submission_evidence
from core.models import Job


def test_submission_evidence_records_package_ats_and_confirmation(tmp_path):
    cv = tmp_path / "cv.pdf"
    cover = tmp_path / "cover.pdf"
    archive = tmp_path / "package.zip"
    cv.write_bytes(b"cv")
    cover.write_bytes(b"cover")
    archive.write_bytes(b"application package")
    package = SimpleNamespace(cv_pdf=cv, cover_letter_pdf=cover, archive=archive)
    job = Job(company="Acme", title="Executive Assistant", location="Remote", source="Lever", url="https://jobs.lever.co/acme/123", description="")

    evidence = build_submission_evidence(
        job,
        7,
        package,
        outcome="submitted",
        message="Application received",
        confirmation_url="https://jobs.lever.co/acme/123/thanks",
        screenshot_path="evidence/confirmation.png",
        attempted_at="2026-08-20T03:30:00+00:00",
    )
    assert evidence.ats == "LEVER"
    assert evidence.outcome == "SUBMITTED"
    assert len(evidence.package_sha256) == 64
    assert evidence.cv_path.endswith("cv.pdf")

    path = persist_submission_evidence(evidence, tmp_path / "evidence")
    payload = json.loads(path.read_text(encoding="utf-8"))
    assert payload["job_id"] == 7
    assert payload["confirmation_url"].endswith("/thanks")
    assert payload["package_sha256"] == evidence.package_sha256

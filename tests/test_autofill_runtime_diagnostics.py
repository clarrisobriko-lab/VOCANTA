import json
from pathlib import Path
from types import SimpleNamespace

import autofill_rehearsal as rehearsal


def test_profile_snapshot_reports_loaded_runtime_values(tmp_path, monkeypatch):
    runtime = tmp_path / "runtime.json"
    canonical = tmp_path / "canonical.json"
    source = tmp_path / "master.docx"
    runtime.write_text("{}", encoding="utf-8")
    canonical.write_text("{}", encoding="utf-8")
    source.write_text("cv", encoding="utf-8")
    monkeypatch.setattr(rehearsal, "APPLICANT_PROFILE_FILE", runtime)
    monkeypatch.setattr(rehearsal, "CANONICAL_PROFILE_FILE", canonical)

    profile = SimpleNamespace(
        full_name="Example Applicant",
        email="applicant@example.com",
        phone="123",
        city="Abuja",
        country="Nigeria",
        postal_code="900106",
        linkedin_url="https://linkedin.example/test",
        notice_period="Available immediately",
        salary_expectation="7.00",
        auto_fill_demographics=True,
        demographics={"gender": "Female"},
        source_resume_path=str(source),
        resume_path="old.pdf",
        highest_education=None,
        employment_history=(1, 2, 3),
    )

    snapshot = rehearsal._profile_snapshot(profile)

    assert snapshot["runtime_profile_exists"] is True
    assert snapshot["canonical_profile_exists"] is True
    assert snapshot["source_resume_exists"] is True
    assert snapshot["postal_code"] == "900106"
    assert snapshot["employment_records"] == 3


def test_write_bundle_creates_json_and_shareable_text(tmp_path):
    json_path = tmp_path / "diagnostics.json"
    text_path = tmp_path / "diagnostics.txt"
    payload = {
        "status": "FAILED",
        "requested_url": "https://example.com/application",
        "runtime": {"git_branch": "main", "git_commit": "abc123"},
        "profile": {"runtime_profile_file": "profile.json"},
        "required_unanswered": ["Gender"],
        "browser_console_errors": ["example error"],
        "page_errors": [],
        "failed_requests": [],
        "exception": "RuntimeError: test",
    }

    rehearsal._write_bundle(json_path, text_path, payload)

    saved = json.loads(json_path.read_text(encoding="utf-8"))
    text = text_path.read_text(encoding="utf-8")
    assert saved["status"] == "FAILED"
    assert "generated_at" in saved
    assert "Required unanswered: ['Gender']" in text
    assert "RuntimeError: test" in text

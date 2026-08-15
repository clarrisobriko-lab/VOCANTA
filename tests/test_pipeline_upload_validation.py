from dataclasses import replace

import pytest

from automation.application_pipeline import validate_browser_documents
from automation.profile import ApplicantProfile


def _profile(tmp_path):
    cv = tmp_path / "cv.pdf"
    cover = tmp_path / "cover.pdf"
    cv.write_bytes(b"%PDF-cv")
    cover.write_bytes(b"%PDF-cover")
    return ApplicantProfile(resume_path=str(cv), cover_letter_path=str(cover))


def test_valid_browser_documents_pass(tmp_path):
    validate_browser_documents(_profile(tmp_path))


def test_missing_cv_fails_closed_before_browser(tmp_path):
    profile = replace(_profile(tmp_path), resume_path=str(tmp_path / "missing.pdf"))
    with pytest.raises(RuntimeError, match="Invalid CV upload"):
        validate_browser_documents(profile)


def test_invalid_optional_supporting_document_fails_closed(tmp_path):
    profile = replace(_profile(tmp_path), supporting_document_path=str(tmp_path / "missing-support.pdf"))
    with pytest.raises(RuntimeError, match="Invalid supporting document upload"):
        validate_browser_documents(profile)

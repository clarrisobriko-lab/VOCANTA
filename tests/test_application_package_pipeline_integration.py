from pathlib import Path
from types import SimpleNamespace

from automation.application_pipeline import profile_for_package, validate_browser_documents


def test_profile_for_package_wires_generated_assets_into_browser_profile(tmp_path):
    cv = tmp_path / "tailored_cv.pdf"
    cover = tmp_path / "cover_letter.pdf"
    support = tmp_path / "certificate.pdf"
    for path in (cv, cover, support):
        path.write_bytes(b"%PDF-1.4\n" + b"x" * 256)

    profile = SimpleNamespace(
        resume_path="old_cv.pdf",
        cover_letter_path="old_cover.pdf",
        supporting_document_path="",
    )
    package = SimpleNamespace(
        cv_pdf=cv,
        cover_letter_pdf=cover,
        supporting_documents=(support,),
    )

    browser_profile = profile_for_package(profile, package)
    assert browser_profile.resume_path == str(cv)
    assert browser_profile.cover_letter_path == str(cover)
    assert browser_profile.supporting_document_path == str(support)


def test_browser_document_validation_accepts_generated_pdf_assets(tmp_path):
    cv = tmp_path / "cv.pdf"
    cover = tmp_path / "cover.pdf"
    cv.write_bytes(b"%PDF-1.4\n" + b"x" * 256)
    cover.write_bytes(b"%PDF-1.4\n" + b"x" * 256)
    profile = SimpleNamespace(resume_path=str(cv), cover_letter_path=str(cover), supporting_document_path="")
    validate_browser_documents(profile)

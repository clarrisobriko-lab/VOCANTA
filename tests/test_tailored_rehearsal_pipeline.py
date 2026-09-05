from pathlib import Path
from types import SimpleNamespace

import autofill_rehearsal as rehearsal
from core.models import Job


def test_prepare_tailored_profile_uses_application_package(monkeypatch):
    job = Job(
        company="PermitFlow",
        title="Administrative Assistant (International)",
        location="Remote",
        source="ASHBY",
        url="https://jobs.ashbyhq.com/permitflow/example/application",
        description="Administrative support role",
    )
    base_profile = object()
    decision = SimpleNamespace(score=88)
    documents = SimpleNamespace(resume_path=Path("Tailored CV.docx"), cover_letter_path=Path("Tailored Cover Letter.docx"))
    package = SimpleNamespace(cv_pdf=Path("PermitFlow CV.pdf"), cover_letter_pdf=Path("PermitFlow Cover Letter.pdf"))
    browser_profile = SimpleNamespace(resume_path=str(package.cv_pdf), cover_letter_path=str(package.cover_letter_pdf))
    calls = []

    class FakeScorer:
        def evaluate(self, candidate):
            calls.append(("score", candidate))
            return decision

    def fake_tailor(candidate, job_id, profile):
        calls.append(("tailor", candidate, job_id, profile))
        return documents

    def fake_package(candidate, docs, scored):
        calls.append(("package", candidate, docs, scored))
        return package

    def fake_profile_for_package(profile, built_package):
        calls.append(("profile", profile, built_package))
        return browser_profile

    monkeypatch.setattr(rehearsal, "Scorer", FakeScorer)
    monkeypatch.setattr(rehearsal, "tailor_documents", fake_tailor)
    monkeypatch.setattr(rehearsal, "build_application_package", fake_package)
    monkeypatch.setattr(rehearsal, "profile_for_package", fake_profile_for_package)

    result = rehearsal._prepare_tailored_profile(job, 42, base_profile)

    assert result == (decision, documents, package, browser_profile)
    assert calls[0] == ("score", job)
    assert calls[1] == ("tailor", job, 42, base_profile)
    assert calls[2] == ("package", job, documents, decision)
    assert calls[3] == ("profile", base_profile, package)
    assert browser_profile.resume_path.endswith("PermitFlow CV.pdf")
    assert "master" not in browser_profile.resume_path.lower()


def test_permitflow_rehearsal_job_id_is_stable():
    url = "https://jobs.ashbyhq.com/permitflow/5b94082e-94f4-46ba-8e21-cfe238e8eae0/application"
    assert rehearsal._rehearsal_job_id(url) == rehearsal._rehearsal_job_id(url)

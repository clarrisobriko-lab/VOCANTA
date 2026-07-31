import json
from pathlib import Path

from automation.diagnostics import ApplicationDiagnostics
from automation.profile import ApplicantProfile, EducationRecord, load_profile, save_profile
from automation.questions import Intent, identify_intent, resolve_question, restriction_reason


def profile(tmp_path: Path) -> ApplicantProfile:
    resume = tmp_path / "cv.docx"; resume.write_bytes(b"cv")
    cover = tmp_path / "cover.docx"; cover.write_bytes(b"cover")
    cert = tmp_path / "cert.pdf"; cert.write_bytes(b"cert")
    return ApplicantProfile(
        first_name="Clarris", middle_name="Phegor", last_name="Obriko",
        email="clarris@example.com", phone="+2348000000000", city="Abuja",
        country="Nigeria", address="Utako", postal_code="900108",
        linkedin_url="https://linkedin.example/clarris", website_url="",
        work_authorization="No, I require employer sponsorship",
        requires_sponsorship=True, notice_period="Immediately available",
        salary_expectation="", nationality="Nigerian", region="Africa",
        highest_education=EducationRecord("University of Uyo", "Bachelor of Laws (LLB)", "Law", "2020", "Nigeria"),
        resume_path=str(resume), cover_letter_path=str(cover), supporting_document_path=str(cert),
    )


def test_question_engine_maps_structured_answers(tmp_path):
    candidate = profile(tmp_path)
    assert identify_intent("What is your current country?") == Intent.CURRENT_COUNTRY
    assert resolve_question("Current country", candidate).value == "Nigeria"
    assert resolve_question("Nationality", candidate).value == "Nigerian"
    assert resolve_question("Degree", candidate).value == "Bachelor of Laws (LLB)"
    assert resolve_question("Field of study", candidate).value == "Law"
    assert resolve_question("Will you require visa sponsorship?", candidate).value == "Yes"


def test_ai_restriction_blocks_automatic_answer(tmp_path):
    candidate = profile(tmp_path)
    label = "I agree to use only my own words in answering this question"
    assert restriction_reason(label)
    resolution = resolve_question(label, candidate)
    assert resolution.auto_fill_allowed is False
    assert "personally authored" in resolution.reason


def test_demographics_remain_opt_in(tmp_path):
    candidate = profile(tmp_path)
    resolution = resolve_question("Gender", candidate)
    assert resolution.intent == Intent.DEMOGRAPHIC
    assert resolution.auto_fill_allowed is False


def test_profile_round_trip_preserves_structured_data(tmp_path):
    candidate = profile(tmp_path)
    path = tmp_path / "profile.json"
    save_profile(candidate, path)
    loaded = load_profile(path)
    assert loaded.highest_education.institution == "University of Uyo"
    assert loaded.employment_history[0].title == "Human Resources Manager"
    assert loaded.preferred_countries[0] == "United Kingdom"


def test_diagnostics_report_is_machine_readable(tmp_path):
    report = ApplicationDiagnostics(
        application_id="GH-3227084", ats="GREENHOUSE", url="https://boards.greenhouse.io/example",
        fields_detected=31, required_fields=28, filled_automatically=24,
        required_manual=4, optional_skipped=3, cv_uploaded=True,
        cover_letter_uploaded=True, submitted=False,
        blocked_reason="Question prohibits AI generated responses",
    )
    path = report.save(tmp_path)
    payload = json.loads(path.read_text(encoding="utf-8"))
    assert payload["application_id"] == "GH-3227084"
    assert payload["completion"] == 86
    assert payload["submission_verified"] is False

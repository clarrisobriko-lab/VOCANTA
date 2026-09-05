import json

from automation.profile import load_profile


def test_runtime_profile_uses_canonical_values(tmp_path, monkeypatch):
    import automation.profile as profile_module

    canonical = tmp_path / "canonical.json"
    runtime = tmp_path / "runtime.json"
    canonical.write_text(json.dumps({
        "first_name": "Clarris",
        "middle_name": "Phegor",
        "last_name": "Obriko",
        "email": "phegclarris@gmail.com",
        "phone": "+2348055632432",
        "city": "Abuja",
        "country": "Nigeria",
        "address": "Abuja, Nigeria",
        "postal_code": "900106",
        "linkedin_url": "https://www.linkedin.com/in/clarris-obriko-880b81104",
        "website_url": "",
        "work_authorization": "No, I require employer sponsorship",
        "requires_sponsorship": True,
        "notice_period": "Available immediately",
        "salary_expectation": "7.00",
        "nationality": "Nigerian",
        "region": "Africa",
        "current_location": "Abuja, Nigeria",
        "open_to_relocation": True,
        "remote_preference": "Remote preferred",
        "preferred_countries": ["United Kingdom"],
        "travel_commitment": "Yes",
        "number_of_employers": "4",
        "highest_education": {"institution": "University of Uyo", "degree": "Bachelor of Laws (LLB)", "discipline": "Law", "graduation_year": "2020", "country": "Nigeria"},
        "employment_history": [],
        "standard_answers": {"how_did_you_hear": "LinkedIn", "salary_expectation": "$7.00 per hour"},
        "demographics": {"gender": "Female", "race": "Black or African American"},
        "auto_fill_demographics": True,
        "privacy_acknowledgements": True
    }), encoding="utf-8")
    runtime.write_text(json.dumps({
        "first_name": "Clarris", "middle_name": "Phegor", "last_name": "Obriko",
        "email": "old@example.com", "phone": "+2340000000000", "city": "Abuja", "country": "Nigeria",
        "address": "Old", "postal_code": "900108", "linkedin_url": "https://linkedin.com/in/old",
        "website_url": "", "work_authorization": "No, I require employer sponsorship", "requires_sponsorship": True,
        "notice_period": "Immediately available", "salary_expectation": "", "demographics": {}, "auto_fill_demographics": False,
        "resume_path": "", "cover_letter_path": "", "supporting_document_path": ""
    }), encoding="utf-8")

    monkeypatch.setattr(profile_module, "CANONICAL_PROFILE_FILE", canonical)
    monkeypatch.setattr(profile_module, "ensure_persistent_assets", lambda: None)
    monkeypatch.setattr(profile_module.ApplicantProfile, "validate", lambda self: [])

    loaded = load_profile(runtime)
    assert loaded.email == "phegclarris@gmail.com"
    assert loaded.postal_code == "900106"
    assert loaded.linkedin_url.endswith("clarris-obriko-880b81104")
    assert loaded.salary_expectation == "7.00"
    assert loaded.demographics["gender"] == "Female"
    assert loaded.demographics["race"] == "Black or African American"
    assert loaded.auto_fill_demographics is True

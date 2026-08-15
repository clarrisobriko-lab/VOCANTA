from intelligence.application_package import (
    ats_match_score,
    build_application_package,
    extract_keywords,
    write_package,
)


def test_extract_keywords_is_deterministic_and_ranked():
    keywords = extract_keywords("Compliance compliance contracts scheduling communication contracts")
    assert keywords[:2] == ("compliance", "contracts")


def test_package_uses_only_candidate_evidence_for_alignment():
    package = build_application_package(
        "Candidate Name",
        "Example Ltd",
        "HR Operations Coordinator",
        "HR operations compliance contracts payroll scheduling Python",
        "HR professional with compliance, contracts and scheduling experience.",
    )
    assert "TARGET ROLE: HR Operations Coordinator" in package.tailored_cv
    assert "compliance" in package.tailored_cv.lower()
    assert "python" not in package.tailored_cv.lower()
    assert "Example Ltd" in package.cover_letter
    assert package.ats_score > 0


def test_ats_score_is_bounded():
    assert ats_match_score("alpha beta", ("alpha", "beta")) == 100
    assert ats_match_score("alpha", ("alpha", "beta")) == 50


def test_package_writer_creates_application_assets(tmp_path):
    package = build_application_package("Candidate", "Acme", "Executive Assistant", "calendar coordination communication", "Calendar coordination professional")
    files = write_package(package, tmp_path)
    assert files["cv"].exists()
    assert files["cover_letter"].exists()
    assert files["keywords"].exists()
    assert "Executive Assistant" in files["cv"].read_text(encoding="utf-8")

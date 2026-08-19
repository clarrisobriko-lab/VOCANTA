from automation.ad_hoc_target_intake import (
    AdHocVacancy,
    IntakeStatus,
    WOMEN_ON_TOP_EXECUTIVE_ASSISTANT,
    intake,
)


def test_women_on_top_target_requires_source_verification():
    result = intake(WOMEN_ON_TOP_EXECUTIVE_ASSISTANT)
    assert result.status == IntakeStatus.NEEDS_SOURCE_VERIFICATION
    assert "official or attributable vacancy source" in result.required_verifications
    assert "verified application channel" in result.required_verifications


def test_verified_target_advances_to_evidence_matching():
    vacancy = AdHocVacancy(
        employer="Women on Top",
        title="Executive Assistant",
        location="Remote",
        work_pattern="Part-time",
        compensation="GBP 200/day",
        responsibilities=("Advanced Excel", "Google Sheets"),
        source_url="https://example.test/vacancy",
        application_url="https://example.test/apply",
        deadline="open and verified",
    )
    result = intake(vacancy)
    assert result.status == IntakeStatus.READY_FOR_EVIDENCE_MATCH
    assert result.required_verifications == ()


def test_missing_identity_fails_closed():
    vacancy = AdHocVacancy("", "", "Remote", "Part-time", "", ())
    assert intake(vacancy).status == IntakeStatus.BLOCKED

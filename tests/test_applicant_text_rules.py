from core.text_rules import has_forbidden_dashes, sanitize_applicant_text


def test_sanitize_removes_em_dash():
    result = sanitize_applicant_text("Legal operations — compliance and coordination")
    assert "—" not in result
    assert result == "Legal operations, compliance and coordination"


def test_sanitize_removes_en_dash():
    result = sanitize_applicant_text("Legal operations – compliance and coordination")
    assert "–" not in result
    assert result == "Legal operations, compliance and coordination"


def test_sanitize_preserves_readable_date_range_without_typographic_dash():
    result = sanitize_applicant_text("January 2025 - Present")
    assert result == "January 2025 Present"
    assert not has_forbidden_dashes(result)


def test_forbidden_dash_detector():
    assert has_forbidden_dashes("one — two")
    assert has_forbidden_dashes("one – two")
    assert not has_forbidden_dashes("one, two")

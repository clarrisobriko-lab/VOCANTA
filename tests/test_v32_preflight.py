from automation.preflight import assess_application_url
from config.settings import APP_VERSION, AUTOMATION_MAX_APPLICATIONS_PER_RUN


def test_version_and_single_application_policy():
    assert APP_VERSION == "3.3.0"
    assert AUTOMATION_MAX_APPLICATIONS_PER_RUN == 1


def test_jobicy_is_rejected_before_browser_launch():
    result = assess_application_url("https://jobicy.com/jobs/147703-example")
    assert result.allowed is False
    assert "jobicy.com" in result.reason


def test_greenhouse_is_supported():
    result = assess_application_url("https://boards.greenhouse.io/example/jobs/123")
    assert result.allowed is True
    assert result.ats == "GREENHOUSE"


def test_generic_site_is_not_automated():
    result = assess_application_url("https://example.com/jobs/123")
    assert result.allowed is False
    assert "Unsupported" in result.reason

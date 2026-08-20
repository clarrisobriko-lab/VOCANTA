import pytest

from automation.live_test_target import PERMITFLOW_ADMINISTRATIVE_ASSISTANT, authorize_target, canonical_url


def test_permitflow_target_is_single_submission_ashby_application():
    target = PERMITFLOW_ADMINISTRATIVE_ASSISTANT
    assert target.allowed_ats == "ASHBY"
    assert target.max_submissions == 1
    assert target.application_url.endswith("/application")
    authorize_target(target.application_url)


def test_tracking_parameters_do_not_change_target_identity():
    target = PERMITFLOW_ADMINISTRATIVE_ASSISTANT
    tracked = target.application_url + "?utm_source=chatgpt.com"
    assert canonical_url(tracked) == canonical_url(target.application_url)
    authorize_target(tracked)


def test_other_vacancy_is_fail_closed():
    with pytest.raises(RuntimeError, match="not the authorized"):
        authorize_target("https://jobs.ashbyhq.com/example/another-role/application")

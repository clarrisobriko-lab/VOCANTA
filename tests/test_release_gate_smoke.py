from automation.ats import adapter_for_url


def test_generic_submission_remains_fail_closed():
    assert adapter_for_url('https://unknown.example/apply').auto_submit_allowed is False

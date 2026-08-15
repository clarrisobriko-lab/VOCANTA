from automation.browser_hardening import classify_page_text


def test_submission_confirmation_is_detected():
    state = classify_page_text("Thank you for applying. Your application has been submitted.")
    assert state.submitted is True
    assert state.account_required is False


def test_account_gate_is_detected_without_claiming_submission():
    state = classify_page_text("Create account or sign in to apply")
    assert state.submitted is False
    assert state.account_required is True


def test_human_challenge_is_never_bypassed():
    state = classify_page_text("Security check: verify you are human")
    assert state.submitted is False
    assert state.human_challenge is True


def test_unknown_state_remains_non_terminal():
    state = classify_page_text("Review your application before continuing")
    assert state.submitted is False
    assert state.account_required is False
    assert state.human_challenge is False

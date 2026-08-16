from intelligence.recipient_discovery import discover_verified_recipient


def test_prefers_explicit_role_mailbox_on_employer_domain():
    text='Questions? email careers@acme.com or jane@acme.com'
    assert discover_verified_recipient(text,'https://jobs.acme.com/123')=='careers@acme.com'


def test_does_not_guess_when_no_email_is_published():
    assert discover_verified_recipient('Join our team today','https://acme.com/jobs')==''


def test_personal_address_is_not_selected_for_automated_follow_up():
    assert discover_verified_recipient('Contact jane.smith@acme.com','https://acme.com/jobs')==''

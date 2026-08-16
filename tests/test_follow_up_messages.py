from intelligence.follow_up_messages import generate_follow_up_message


def test_first_follow_up_contains_job_context():
    message=generate_follow_up_message("Acme","Executive Assistant","Test Candidate","FIRST_FOLLOW_UP")
    assert message.subject=="Follow-up on application for Executive Assistant"
    assert "Executive Assistant position at Acme" in message.body
    assert message.body.endswith("Kind regards,\nTest Candidate")


def test_second_follow_up_is_distinct():
    message=generate_follow_up_message("Acme","HR Coordinator","Test Candidate","SECOND_FOLLOW_UP")
    assert "following up once more" in message.body


def test_message_does_not_claim_unverified_contact_or_interview():
    message=generate_follow_up_message("Acme","Legal Officer","Test Candidate","FIRST_FOLLOW_UP")
    lowered=message.body.lower()
    assert "interview" not in lowered
    assert "your email" not in lowered

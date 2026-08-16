from intelligence.application_progress import classify_progress


def test_interview_invitation_is_detected():
    signal=classify_progress('Interview invitation','We would like to invite you to interview next week.')
    assert signal.status=='INTERVIEW'
    assert signal.confidence>=90


def test_offer_is_detected_before_generic_positive_language():
    signal=classify_progress('Job offer','We are pleased to offer you the position.')
    assert signal.status=='OFFER'


def test_rejection_is_detected():
    signal=classify_progress('Application update','Unfortunately, we will not be moving forward with your application.')
    assert signal.status=='REJECTED'


def test_acknowledgement_is_not_misclassified_as_interview():
    signal=classify_progress('Application received','Thank you for applying. We received your application.')
    assert signal.status=='APPLIED'


def test_ambiguous_message_remains_unknown():
    signal=classify_progress('Hello','Please visit our careers page.')
    assert signal.status=='UNKNOWN'

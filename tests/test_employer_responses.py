from intelligence.employer_responses import classify_employer_response


def test_offer_is_detected():
    result=classify_employer_response('Your offer','We are pleased to offer you the position.')
    assert result.status=='OFFER'
    assert result.confidence>=90


def test_interview_is_detected():
    result=classify_employer_response('Next steps','We would like to schedule a conversation with you.')
    assert result.status=='INTERVIEW'


def test_rejection_is_detected():
    result=classify_employer_response('Application update','Unfortunately, we will not be moving forward with your application.')
    assert result.status=='REJECTED'


def test_information_request_is_detected():
    result=classify_employer_response('Application','Could you provide additional information about your availability?')
    assert result.status=='ACTION_REQUIRED'


def test_ambiguous_response_requires_review():
    result=classify_employer_response('Hello','Thank you for your message. We will be in touch.')
    assert result.status=='REVIEW'

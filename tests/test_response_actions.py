from intelligence.employer_responses import EmployerResponse
from intelligence.response_actions import action_for_response


def test_offer_is_urgent():
    action=action_for_response(EmployerResponse('OFFER',95,'offer'))
    assert action.priority=='URGENT'
    assert 'offer' in action.action.lower()


def test_interview_is_high_priority():
    assert action_for_response(EmployerResponse('INTERVIEW',90,'interview')).priority=='HIGH'


def test_action_required_is_high_priority():
    assert action_for_response(EmployerResponse('ACTION_REQUIRED',80,'request')).priority=='HIGH'


def test_review_is_manual():
    action=action_for_response(EmployerResponse('REVIEW',40,'unclear'))
    assert action.priority=='MEDIUM'
    assert 'manually' in action.action.lower()

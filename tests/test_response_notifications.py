from automation.response_notifications import build_response_notification, deliver_response_notifications
from intelligence.employer_responses import EmployerResponse


class Sender:
    def __init__(self): self.sent=[]
    def send(self,subject,body): self.sent.append((subject,body))


def test_offer_creates_urgent_notification():
    note=build_response_notification('m1','Acme','Counsel','talent@acme.com',EmployerResponse('OFFER',95,'offer'))
    assert note is not None
    assert note.priority=='URGENT'
    assert 'Acme' in note.subject


def test_interview_creates_high_priority_notification():
    note=build_response_notification('m2','Acme','Counsel','talent@acme.com',EmployerResponse('INTERVIEW',90,'interview'))
    assert note is not None
    assert note.priority=='HIGH'


def test_rejection_does_not_interrupt_user():
    assert build_response_notification('m3','Acme','Counsel','talent@acme.com',EmployerResponse('REJECTED',88,'rejected')) is None


def test_delivery_returns_message_ids():
    sender=Sender(); note=build_response_notification('m1','Acme','Counsel','talent@acme.com',EmployerResponse('OFFER',95,'offer'))
    assert deliver_response_notifications([note],sender)==['m1']
    assert len(sender.sent)==1

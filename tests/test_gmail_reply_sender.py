import base64
from email import message_from_bytes

from automation.gmail_reply_sender import GmailReplySender


class Call:
    def __init__(self,result): self.result=result
    def execute(self): return self.result


class Messages:
    def __init__(self): self.body=None
    def send(self,userId,body): self.body=body; return Call({'id':'sent1'})


class Users:
    def __init__(self,messages): self.messages_api=messages
    def messages(self): return self.messages_api


class Service:
    def __init__(self): self.messages_api=Messages(); self.users_api=Users(self.messages_api)
    def users(self): return self.users_api


def test_reply_stays_in_gmail_thread():
    service=Service(); sender=GmailReplySender(service,'candidate@example.com')
    sent=sender.send('talent@acme.com','Re: Interview','Thank you',thread_id='thread1',in_reply_to='<original@acme.com>',references='<earlier@acme.com>')
    assert sent=='sent1'
    assert service.messages_api.body['threadId']=='thread1'
    raw=base64.urlsafe_b64decode(service.messages_api.body['raw']); message=message_from_bytes(raw)
    assert message['In-Reply-To']=='<original@acme.com>'
    assert '<earlier@acme.com>' in message['References']
    assert '<original@acme.com>' in message['References']

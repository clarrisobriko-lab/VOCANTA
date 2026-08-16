import base64

from automation.gmail_source import GmailInboxSource


def encoded(text): return base64.urlsafe_b64encode(text.encode()).decode().rstrip('=')


def test_normalizes_gmail_message():
    raw={'id':'m1','snippet':'fallback','payload':{'mimeType':'multipart/alternative','headers':[{'name':'From','value':'Recruiter <talent@acme.com>'},{'name':'Subject','value':'Interview invitation'},{'name':'Date','value':'Sun, 16 Aug 2026 10:00:00 +0000'}],'parts':[{'mimeType':'text/plain','body':{'data':encoded('We would like to schedule an interview.')}}]}}
    message=GmailInboxSource._normalize(raw)
    assert message['id']=='m1'
    assert message['from']=='talent@acme.com'
    assert message['subject']=='Interview invitation'
    assert 'schedule an interview' in message['body']


def test_uses_snippet_when_plain_text_body_missing():
    raw={'id':'m2','snippet':'Application update','payload':{'headers':[]}}
    assert GmailInboxSource._normalize(raw)['body']=='Application update'

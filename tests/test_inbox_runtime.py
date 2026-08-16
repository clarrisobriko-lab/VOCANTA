from inbox_runtime import normalize_mail_message, summarize_inbox_results
from automation.inbox_ingestion import InboxResult


def test_normalizes_connector_style_message():
    message=normalize_mail_message({'message_id':'abc','sender':'talent@acme.com','subject':'Interview','text':'Schedule a call','received_at':'2026-08-16'})
    assert message['id']=='abc'
    assert message['from']=='talent@acme.com'
    assert message['body']=='Schedule a call'


def test_summarizes_ingestion_results():
    results=[InboxResult('1','PROCESSED',1),InboxResult('2','UNMATCHED'),InboxResult('3','DUPLICATE',1),InboxResult('','INVALID')]
    assert summarize_inbox_results(results)=={'processed':1,'duplicate':1,'unmatched':1,'invalid':1}

from inbox_runtime import notify_retention_volume, retention_alert_required


class AlertSender:
    def __init__(self): self.messages=[]
    def send(self,subject,body): self.messages.append((subject,body)); return 'sent'


def test_retention_alert_fires_at_configured_threshold():
    sender=AlertSender(); retention={'archived_replies':40,'audit_events':60}
    assert retention_alert_required(retention,100)
    assert notify_retention_volume(retention,sender,100)
    assert len(sender.messages)==1
    subject,body=sender.messages[0]
    assert subject=='VOCANTA retention volume alert'
    assert '40 archived replies' in body
    assert '60 audit events' in body
    assert 'Total removed: 100' in body


def test_retention_alert_stays_quiet_below_threshold():
    sender=AlertSender(); retention={'archived_replies':10,'audit_events':20}
    assert not retention_alert_required(retention,100)
    assert not notify_retention_volume(retention,sender,100)
    assert sender.messages==[]


def test_retention_alert_failure_does_not_break_runtime_notification_path():
    class BrokenSender:
        def send(self,subject,body): raise RuntimeError('smtp unavailable')
    assert not notify_retention_volume({'archived_replies':100,'audit_events':0},BrokenSender(),100)

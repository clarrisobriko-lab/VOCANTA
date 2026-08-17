import sqlite3

from inbox_runtime import notify_retention_volume


class Sender:
    def __init__(self): self.calls=[]
    def send(self,subject,body): self.calls.append((subject,body)); return 'ok'


def test_same_retention_volume_alert_is_sent_once():
    connection=sqlite3.connect(':memory:'); sender=Sender(); retention={'archived_replies':60,'audit_events':40}
    assert notify_retention_volume(retention,sender,threshold=100,connection=connection) is True
    assert notify_retention_volume(retention,sender,threshold=100,connection=connection) is False
    assert len(sender.calls)==1


def test_different_retention_volume_can_alert_again():
    connection=sqlite3.connect(':memory:'); sender=Sender()
    assert notify_retention_volume({'archived_replies':60,'audit_events':40},sender,threshold=100,connection=connection) is True
    assert notify_retention_volume({'archived_replies':61,'audit_events':40},sender,threshold=100,connection=connection) is True
    assert len(sender.calls)==2

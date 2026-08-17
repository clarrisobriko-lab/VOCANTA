from automation.application_pipeline import _apply_with_recovery
from automation.browser import AutomationResult


class _Job:
    url='https://jobs.lever.co/acme/123'


class _Engine:
    calls=0
    def apply(self,url,job_id):
        type(self).calls+=1
        return AutomationResult('UNKNOWN','submit clicked but confirmation missing','',5)


def test_unknown_submission_is_never_automatically_retried():
    _Engine.calls=0
    result=_apply_with_recovery(_Job(),1,object(),lambda profile:_Engine(),max_attempts=3,sleep_fn=lambda _:None)
    assert result.status=='UNKNOWN'
    assert _Engine.calls==1

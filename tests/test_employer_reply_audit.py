import sqlite3

from core.employer_reply_store import approve_reply_draft, save_reply_draft, update_reply_draft
from intelligence.employer_reply_drafts import build_reply_draft


def test_reply_lifecycle_is_audited():
    c=sqlite3.connect(':memory:')
    draft=build_reply_draft('INTERVIEW','Acme','Counsel','Candidate','Interview')
    assert save_reply_draft(c,'m1',1,draft)
    assert update_reply_draft(c,'m1','Re: Interview','Thank you. I am available.')
    assert approve_reply_draft(c,'m1')
    events=[row[0] for row in c.execute("SELECT event FROM employer_reply_audit WHERE message_id='m1' ORDER BY id").fetchall()]
    assert events==['CREATED','EDITED','APPROVED']

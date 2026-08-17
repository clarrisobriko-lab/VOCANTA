import sqlite3

from analytics import reply_audit
from core.employer_reply_store import approve_reply_draft, save_reply_draft, update_reply_draft
from intelligence.employer_reply_drafts import build_reply_draft


def test_dashboard_reads_reply_audit_in_newest_first_order():
    c=sqlite3.connect(':memory:')
    c.execute("CREATE TABLE jobs(id INTEGER PRIMARY KEY,company TEXT,title TEXT)")
    c.execute("INSERT INTO jobs VALUES(1,'Acme','Counsel')")
    draft=build_reply_draft('INTERVIEW','Acme','Counsel','Candidate','Interview')
    save_reply_draft(c,'m1',1,draft)
    update_reply_draft(c,'m1','Re: Interview','Thank you. I am available.')
    approve_reply_draft(c,'m1')
    history=reply_audit(c)
    assert [item['event'] for item in history[:3]]==['APPROVED','EDITED','CREATED']
    assert all(item['company']=='Acme' for item in history[:3])
    assert all(item['title']=='Counsel' for item in history[:3])

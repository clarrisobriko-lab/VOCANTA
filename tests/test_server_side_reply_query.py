import sqlite3

from analytics import query_reply_records
from core.employer_reply_store import save_reply_draft
from intelligence.employer_reply_drafts import build_reply_draft


def test_server_query_filters_before_pagination():
    c=sqlite3.connect(':memory:')
    c.execute("CREATE TABLE jobs(id INTEGER PRIMARY KEY,company TEXT,title TEXT)")
    c.execute("INSERT INTO jobs VALUES(1,'Acme','Counsel')")
    c.execute("INSERT INTO jobs VALUES(2,'Beta','Solicitor')")
    for i in range(15):
        job=1 if i<12 else 2
        company='Acme' if job==1 else 'Beta'
        save_reply_draft(c,f'm{i}',job,build_reply_draft('INTERVIEW',company,'Counsel','Candidate',f'Interview {i}'))
    items,meta=query_reply_records(c,'pending','acme',2,5)
    assert len(items)==5
    assert meta=={'page':2,'pages':3,'total':12,'page_size':5}
    assert all(item['company']=='Acme' for item in items)


def test_server_query_searches_audit_detail():
    c=sqlite3.connect(':memory:')
    c.execute("CREATE TABLE jobs(id INTEGER PRIMARY KEY,company TEXT,title TEXT)")
    c.execute("INSERT INTO jobs VALUES(1,'Acme','Counsel')")
    save_reply_draft(c,'m1',1,build_reply_draft('INTERVIEW','Acme','Counsel','Candidate','Interview'))
    items,meta=query_reply_records(c,'audit','Interview',1,10)
    assert meta['total']>=1
    assert any(item['message_id']=='m1' for item in items)

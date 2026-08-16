import sqlite3

from reply_operator import list_pending, show_reply


def db():
    c=sqlite3.connect(':memory:')
    c.execute('CREATE TABLE jobs(id INTEGER PRIMARY KEY,company TEXT,title TEXT)')
    c.execute("CREATE TABLE employer_reply_drafts(message_id TEXT PRIMARY KEY,job_id INTEGER,subject TEXT,body TEXT,status TEXT,created_at TEXT)")
    c.execute("CREATE TABLE employer_responses(message_id TEXT PRIMARY KEY,sender TEXT)")
    c.execute("INSERT INTO jobs VALUES(1,'Acme','Counsel')")
    c.execute("INSERT INTO employer_reply_drafts VALUES('m1',1,'Re: Interview','Thank you','AWAITING_APPROVAL','2026-08-16T00:00:00Z')")
    c.execute("INSERT INTO employer_responses VALUES('m1','talent@acme.com')")
    return c


def test_list_pending_returns_review_queue():
    rows=list_pending(db())
    assert len(rows)==1
    assert rows[0][0]=='m1'
    assert rows[0][1]=='Acme'


def test_show_reply_includes_recipient_and_status():
    row=show_reply(db(),'m1')
    assert row[5]=='AWAITING_APPROVAL'
    assert row[6]=='talent@acme.com'

import sqlite3

from automation.inbox_ingestion import process_inbox_messages


def db():
    c=sqlite3.connect(":memory:")
    c.execute("CREATE TABLE jobs(id INTEGER PRIMARY KEY,company TEXT,title TEXT,url TEXT,applied INTEGER,status TEXT,updated_at TEXT)")
    c.execute("CREATE TABLE application_history(id INTEGER PRIMARY KEY AUTOINCREMENT,job_id INTEGER,old_status TEXT,new_status TEXT,notes TEXT,changed_at TEXT)")
    c.execute("INSERT INTO jobs VALUES(1,'Acme','Executive Assistant','https://acme.com/jobs/1',1,'APPLIED',NULL)")
    return c


def test_matching_interview_message_updates_job():
    c=db(); messages=[{'id':'m1','from':'talent@acme.com','subject':'Executive Assistant interview','body':'We would like to schedule a conversation.'}]
    result=process_inbox_messages(c,messages)
    assert result[0].status=='PROCESSED'
    assert result[0].job_id==1
    assert c.execute("SELECT status FROM jobs WHERE id=1").fetchone()[0]=='INTERVIEW'


def test_unrelated_message_is_not_attached_to_application():
    c=db(); messages=[{'id':'m2','from':'newsletter@example.org','subject':'Weekly news','body':'Hello reader'}]
    result=process_inbox_messages(c,messages)
    assert result[0].status=='UNMATCHED'


def test_duplicate_message_is_safe():
    c=db(); message={'id':'m1','from':'talent@acme.com','subject':'Executive Assistant interview','body':'Interview availability'}
    assert process_inbox_messages(c,[message])[0].status=='PROCESSED'
    assert process_inbox_messages(c,[message])[0].status=='DUPLICATE'

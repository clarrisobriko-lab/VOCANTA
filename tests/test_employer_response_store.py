import sqlite3

from core.employer_response_store import record_employer_response
from intelligence.employer_responses import EmployerResponse


def db():
    c=sqlite3.connect(":memory:")
    c.execute("CREATE TABLE jobs(id INTEGER PRIMARY KEY,status TEXT,updated_at TEXT)")
    c.execute("CREATE TABLE application_history(id INTEGER PRIMARY KEY AUTOINCREMENT,job_id INTEGER,old_status TEXT,new_status TEXT,notes TEXT,changed_at TEXT)")
    c.execute("INSERT INTO jobs VALUES(1,'APPLIED',NULL)")
    return c


def test_interview_updates_application_status():
    c=db(); response=EmployerResponse('INTERVIEW',90,'interview language detected')
    assert record_employer_response(c,1,'m1','recruiter@acme.com','Interview',response)
    assert c.execute("SELECT status FROM jobs WHERE id=1").fetchone()[0]=='INTERVIEW'
    assert c.execute("SELECT new_status FROM application_history").fetchone()[0]=='INTERVIEW'


def test_duplicate_message_is_idempotent():
    c=db(); response=EmployerResponse('OFFER',95,'offer language detected')
    assert record_employer_response(c,1,'m1','jobs@acme.com','Offer',response)
    assert record_employer_response(c,1,'m1','jobs@acme.com','Offer',response) is False
    assert c.execute("SELECT COUNT(*) FROM employer_responses").fetchone()[0]==1


def test_review_does_not_change_application_status():
    c=db(); response=EmployerResponse('REVIEW',40,'human review')
    record_employer_response(c,1,'m1','hello@acme.com','Update',response)
    assert c.execute("SELECT status FROM jobs WHERE id=1").fetchone()[0]=='APPLIED'

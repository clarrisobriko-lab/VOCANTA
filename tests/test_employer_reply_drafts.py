import sqlite3

from core.employer_reply_store import approve_reply_draft, save_reply_draft
from intelligence.employer_reply_drafts import build_reply_draft


def test_interview_draft_requires_approval():
    draft=build_reply_draft('INTERVIEW','Acme','Counsel','Test Candidate','Interview invitation')
    assert draft is not None
    assert draft.requires_approval is True
    assert draft.subject=='Re: Interview invitation'
    assert 'available interview times' in draft.body


def test_offer_draft_does_not_accept_offer():
    draft=build_reply_draft('OFFER','Acme','Counsel','Test Candidate','Your offer')
    assert draft is not None
    assert 'review the terms carefully' in draft.body
    assert 'accept' not in draft.body.lower()


def test_rejection_does_not_generate_reply():
    assert build_reply_draft('REJECTED','Acme','Counsel','Test Candidate') is None


def test_saved_draft_waits_for_explicit_approval():
    c=sqlite3.connect(':memory:'); draft=build_reply_draft('ACTION_REQUIRED','Acme','Counsel','Test Candidate','More information')
    assert save_reply_draft(c,'m1',1,draft)
    assert c.execute("SELECT status FROM employer_reply_drafts WHERE message_id='m1'").fetchone()[0]=='AWAITING_APPROVAL'
    assert approve_reply_draft(c,'m1')
    assert c.execute("SELECT status FROM employer_reply_drafts WHERE message_id='m1'").fetchone()[0]=='APPROVED'

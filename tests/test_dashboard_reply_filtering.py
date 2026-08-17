from analytics import filter_records


def test_reply_filter_matches_company_role_subject_and_identifier():
    records=[
        {'company':'Acme','title':'Counsel','subject':'Interview','gmail_message_id':'gmail123'},
        {'company':'Beta','title':'Solicitor','subject':'Offer','gmail_message_id':'gmail456'},
    ]
    assert [r['company'] for r in filter_records(records,'acme')]==['Acme']
    assert [r['company'] for r in filter_records(records,'solicitor')]==['Beta']
    assert [r['company'] for r in filter_records(records,'offer')]==['Beta']
    assert [r['company'] for r in filter_records(records,'GMAIL123')]==['Acme']
    assert filter_records(records,'missing')==[]
    assert filter_records(records,'')==records

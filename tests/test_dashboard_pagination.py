from analytics import paginate_records


def test_paginate_records_clamps_pages_and_preserves_order():
    records=[{'id':index} for index in range(23)]
    first,meta=paginate_records(records,1,10)
    assert [item['id'] for item in first]==list(range(10))
    assert meta=={'page':1,'pages':3,'total':23,'page_size':10}
    last,meta=paginate_records(records,99,10)
    assert [item['id'] for item in last]==[20,21,22]
    assert meta['page']==3


def test_paginate_records_handles_empty_input():
    page,meta=paginate_records([],1,10)
    assert page==[]
    assert meta['page']==1
    assert meta['pages']==1
    assert meta['total']==0

from automation.ats import ADAPTERS


def test_supported_ats_matrix_is_complete():
    assert {a.name for a in ADAPTERS} == {'GREENHOUSE','LEVER','ASHBY','SMARTRECRUITERS','WORKDAY'}

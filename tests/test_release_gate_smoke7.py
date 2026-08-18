from automation.ats import GENERIC_ADAPTER


def test_generic_adapter_is_explicitly_non_production():
    assert GENERIC_ADAPTER.name=='GENERIC'
    assert GENERIC_ADAPTER.auto_submit_allowed is False

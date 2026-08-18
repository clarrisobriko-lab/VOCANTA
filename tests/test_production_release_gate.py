from automation.ats import ADAPTERS, GENERIC_ADAPTER, adapter_for_url


def test_all_supported_adapters_are_explicitly_auto_submit_capable():
    assert {a.name for a in ADAPTERS}=={'GREENHOUSE','LEVER','ASHBY','SMARTRECRUITERS','WORKDAY'}
    assert all(a.auto_submit_allowed for a in ADAPTERS)


def test_unknown_platform_is_never_auto_submit_capable():
    assert adapter_for_url('https://example.org/apply') is GENERIC_ADAPTER
    assert GENERIC_ADAPTER.auto_submit_allowed is False

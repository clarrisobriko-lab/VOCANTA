from automation.ats import ADAPTERS


def test_production_adapters_are_enabled():
    assert all(adapter.auto_submit_allowed for adapter in ADAPTERS)

from automation.ats import ADAPTERS


def test_supported_adapter_count():
    assert len(ADAPTERS)==5

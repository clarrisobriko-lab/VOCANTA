from automation.ats import ADAPTERS


def test_adapter_names_are_uppercase():
    assert all(a.name==a.name.upper() for a in ADAPTERS)

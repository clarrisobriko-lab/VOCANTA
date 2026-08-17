from automation.ats import ADAPTERS


def test_adapter_host_markers_are_unique():
    markers=[m for a in ADAPTERS for m in a.host_markers]
    assert len(markers)==len(set(markers))

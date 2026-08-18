from automation.ats import ADAPTERS


def test_every_supported_adapter_has_submit_control_text():
    assert all(any(text.strip() for text in a.final_submit_texts) for a in ADAPTERS)

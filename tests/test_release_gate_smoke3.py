from automation.ats import ADAPTERS


def test_supported_ats_require_confirmation_contracts():
    assert all(a.confirmation_phrases and a.final_submit_texts for a in ADAPTERS)

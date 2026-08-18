from automation.ats import ADAPTERS


def test_confirmation_evidence_is_nonempty():
    assert all(all(p.strip() for p in a.confirmation_phrases) for a in ADAPTERS)

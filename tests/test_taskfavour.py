from connectors.taskfavour import _eligible_remote


def test_worldwide_remote_is_eligible():
    assert _eligible_remote("Executive Assistant, Remote Worldwide")


def test_africa_remote_is_eligible():
    assert _eligible_remote("Operations Coordinator, Remote Africa")


def test_nigeria_remote_is_eligible():
    assert _eligible_remote("HR Assistant, remote, Nigeria")


def test_us_only_remote_is_rejected():
    assert not _eligible_remote("Remote, United States only")


def test_hybrid_is_rejected_even_if_remote_word_present():
    assert not _eligible_remote("Hybrid remote role, Worldwide team")


def test_plain_remote_without_eligibility_evidence_is_rejected():
    assert not _eligible_remote("Administrative Assistant, Remote")

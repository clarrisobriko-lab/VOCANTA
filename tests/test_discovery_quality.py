from connectors.hidden_sources import normalize_outbound_url, source_quality


def test_tracking_parameters_are_removed_for_cross_source_deduplication():
    url = normalize_outbound_url("https://www.jobs.lever.co/acme/123?utm_source=board&ref=foo&team=ops")
    assert url == "https://jobs.lever.co/acme/123?team=ops"


def test_direct_ats_link_gets_high_reliability():
    allowed, location, reliability = source_quality("Remote worldwide Executive Assistant", "https://jobs.lever.co/acme/123")
    assert allowed is True
    assert location == "Remote, international"
    assert reliability == "HIGH"


def test_explicit_geo_restriction_is_suppressed():
    allowed, _, reliability = source_quality("Executive Assistant, US only", "https://careers.example.com/jobs/1")
    assert allowed is False
    assert reliability == "RESTRICTED"


def test_navigation_links_are_suppressed():
    allowed, _, reliability = source_quality("Privacy", "https://example.com/privacy")
    assert allowed is False
    assert reliability == "LOW"


def test_non_ats_employer_link_remains_discoverable():
    allowed, location, reliability = source_quality("Remote HR Operations Coordinator", "https://careers.example.com/jobs/2")
    assert allowed is True
    assert location == "Remote"
    assert reliability == "MEDIUM"

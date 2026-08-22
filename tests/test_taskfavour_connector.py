from bs4 import BeautifulSoup

from connectors.taskfavour import _best_application_url, _eligible_remote


def test_accepts_worldwide_remote_role():
    assert _eligible_remote("Executive Assistant, Remote, Worldwide")


def test_accepts_nigeria_or_africa_remote_role():
    assert _eligible_remote("Operations Coordinator, remote across Africa")
    assert _eligible_remote("Administrative Assistant, Nigeria remote")


def test_rejects_country_restricted_and_hybrid_roles():
    assert not _eligible_remote("Remote, United States only")
    assert not _eligible_remote("Hybrid role in London")
    assert not _eligible_remote("Remote, must be based in Canada")


def test_prefers_direct_employer_ats_link_over_aggregator_listing():
    card = BeautifulSoup(
        '<article><a href="/job/example">Listing</a>'
        '<a href="https://jobs.ashbyhq.com/example/123">Apply now</a></article>',
        "html.parser",
    )
    assert _best_application_url(card, "https://www.taskfavour.com/job/example") == "https://jobs.ashbyhq.com/example/123"


def test_falls_back_to_listing_when_no_supported_ats_is_exposed():
    card = BeautifulSoup('<article><a href="/job/example">Listing</a></article>', "html.parser")
    assert _best_application_url(card, "https://www.taskfavour.com/job/example") == "https://www.taskfavour.com/job/example"

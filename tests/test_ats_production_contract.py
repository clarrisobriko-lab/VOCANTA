import pytest

from automation.ats import ADAPTERS, GENERIC_ADAPTER, adapter_for_url


@pytest.mark.parametrize(
    ('url','name'),
    [
        ('https://boards.greenhouse.io/acme/jobs/1','GREENHOUSE'),
        ('https://jobs.lever.co/acme/1','LEVER'),
        ('https://jobs.ashbyhq.com/acme/1','ASHBY'),
        ('https://jobs.smartrecruiters.com/acme/1','SMARTRECRUITERS'),
        ('https://acme.wd5.myworkdayjobs.com/jobs/1','WORKDAY'),
    ],
)
def test_supported_ats_routes_to_explicit_auto_submit_adapter(url, name):
    adapter=adapter_for_url(url)
    assert adapter.name==name
    assert adapter.auto_submit_allowed is True
    assert adapter.final_submit_texts
    assert adapter.confirmation_phrases


def test_generic_and_unknown_hosts_fail_closed():
    adapter=adapter_for_url('https://careers.example.com/jobs/1')
    assert adapter is GENERIC_ADAPTER
    assert adapter.auto_submit_allowed is False


def test_every_production_adapter_has_unique_name_and_hosts():
    names=[adapter.name for adapter in ADAPTERS]
    assert len(names)==len(set(names))
    hosts=[marker for adapter in ADAPTERS for marker in adapter.host_markers]
    assert len(hosts)==len(set(hosts))


def test_every_production_adapter_requires_confirmation_evidence():
    for adapter in ADAPTERS:
        assert adapter.confirmation_phrases
        assert all(phrase.strip() for phrase in adapter.confirmation_phrases)

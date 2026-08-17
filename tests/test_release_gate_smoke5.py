from automation.ats import adapter_for_url


def test_production_adapter_routing():
    cases={'https://boards.greenhouse.io/a':'GREENHOUSE','https://jobs.lever.co/a':'LEVER','https://jobs.ashbyhq.com/a':'ASHBY','https://jobs.smartrecruiters.com/a':'SMARTRECRUITERS','https://a.myworkdayjobs.com/a':'WORKDAY'}
    assert {adapter_for_url(url).name for url in cases}==set(cases.values())

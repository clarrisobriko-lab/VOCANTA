from automation.portfolio_targeting import PortfolioJob, TargetingPolicy, eligible, select_target


def test_engineering_roles_are_excluded():
    job=PortfolioJob('Applied AI Engineer','https://example.test/ai','Engineering',remote_global=True)
    assert eligible(job,TargetingPolicy()) is False


def test_selects_best_eligible_role_without_human_role_choice():
    jobs=[
        PortfolioJob('Applied AI Engineer','https://example.test/ai','Engineering',remote_global=True),
        PortfolioJob('Technical Account Manager','https://example.test/tam','Customer Success',remote_global=True),
        PortfolioJob('Strategic Finance Manager','https://example.test/finance','Finance',remote_global=True),
    ]
    target=select_target(jobs)
    assert target is not None
    assert target.title=='Technical Account Manager'


def test_returns_none_when_portfolio_has_no_eligible_target():
    jobs=[PortfolioJob('Experienced Software Engineer','https://example.test/swe','Engineering',remote_global=True)]
    assert select_target(jobs) is None

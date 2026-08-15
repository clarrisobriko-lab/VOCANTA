from core.models import Job
from intelligence.opportunity_intelligence import analyse_opportunity, employer_score, salary_score


def job(**changes):
    values = dict(company="Acme", title="HR Operations Coordinator", location="Remote worldwide", source="Lever", url="https://jobs.lever.co/acme/123", salary="$50,000 - $70,000 per year", description="HR operations onboarding recruitment compliance scheduling")
    values.update(changes)
    return Job(**values)


def test_salary_scoring_rewards_clear_compensation():
    assert salary_score("$50,000 - $70,000 per year") >= 85
    assert salary_score("") == 50


def test_global_remote_direct_ats_employer_scores_highly():
    assert employer_score(job()) >= 90


def test_opportunity_intelligence_exposes_skill_gaps_and_composite():
    result = analyse_opportunity(job(description="HR operations onboarding recruitment compliance Salesforce"))
    assert result.skill_gap_score >= 0
    assert isinstance(result.missing_skills, tuple)
    assert 0 <= result.opportunity_score <= 100
    assert result.salary_text

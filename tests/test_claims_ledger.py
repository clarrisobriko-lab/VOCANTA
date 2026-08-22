from automation.ats_match import analyse_ats_match, verified_job_keywords
from automation.claims_ledger import evidence_for, verified_skill_keys
from core.models import Job


def job(description: str) -> Job:
    return Job(company="Example", title="Operations Role", location="Remote", description=description, url="https://example.com/job", source="test")


def test_every_verified_skill_has_evidence():
    assert verified_skill_keys()
    assert all(evidence_for(skill) for skill in verified_skill_keys())


def test_supported_requirement_is_matched_from_ledger():
    result = analyse_ats_match(job("The role requires recruitment, onboarding and compliance experience."))
    assert "recruitment" in result.matched_skills
    assert "onboarding" in result.matched_skills
    assert "compliance" in result.matched_skills


def test_unsupported_vacancy_requirement_stays_missing():
    result = analyse_ats_match(job("Experience with Salesforce and Workday is required."))
    assert "salesforce" in result.missing_skills
    assert "workday" in result.missing_skills
    assert "salesforce" not in verified_job_keywords(job("Salesforce required"))
    assert "workday" not in verified_job_keywords(job("Workday required"))


def test_unverified_collaboration_tools_remain_gaps():
    result = analyse_ats_match(job("Daily collaboration through Slack and Zoom is required."))
    assert "slack" in result.missing_skills
    assert "zoom" in result.missing_skills


def test_inferred_project_and_workflow_claims_remain_gaps():
    result = analyse_ats_match(job("Project coordination and workflow management experience required."))
    assert "project coordination" in result.missing_skills
    assert "workflow management" in result.missing_skills


def test_vacancy_cannot_create_new_applicant_claim():
    before = verified_skill_keys()
    verified_job_keywords(job("Must have Salesforce, Workday and Google Workspace expertise."))
    assert verified_skill_keys() == before

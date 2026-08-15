from core.models import Job
from intelligence.employer_intelligence import analyse_job, detect_skills, extract_salary_text


def make_job(**changes):
    data = dict(company="Acme", title="HR Operations Coordinator", location="Remote worldwide", source="Test", url="https://jobs.lever.co/acme/123", description="Manage onboarding, recruitment, compliance, stakeholder communication and Workday. Salary $55,000 - $65,000 per year.", salary="")
    data.update(changes)
    return Job(**data)


def test_semantic_skill_detection():
    skills = detect_skills(make_job())
    assert "human resources" in skills
    assert "recruitment" in skills
    assert "onboarding" in skills
    assert "compliance" in skills
    assert "workday" in skills


def test_salary_is_extracted_when_structured_salary_missing():
    assert extract_salary_text(make_job()).startswith("$55,000")


def test_structured_salary_wins():
    assert extract_salary_text(make_job(salary="£40,000 per year")) == "£40,000 per year"


def test_job_intelligence_includes_employer_domain_remote_and_interview_prediction():
    intel = analyse_job(make_job())
    assert intel.employer_domain == "jobs.lever.co"
    assert intel.remote_signal == "GLOBAL_REMOTE"
    assert intel.likely_interview_questions
    assert any("onboarding" in question for question in intel.likely_interview_questions)

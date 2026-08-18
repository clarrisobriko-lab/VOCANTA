from automation.employer_dry_run import CandidateEvidence, DryRunStatus, EmployerVacancy, run_employer_dry_run
from automation.portfolio_targeting import PortfolioJob


def vacancy(title, category, *, skills=(), documents=("cv",), payment=False, financial=False):
    return EmployerVacancy(
        PortfolioJob(title, f"https://example.test/{title.lower().replace(' ', '-')}", category),
        frozenset(skills), frozenset(documents), payment, financial,
    )


def test_selects_ready_non_engineering_vacancy_from_employer_portfolio():
    vacancies = [
        vacancy("Software Engineer", "Engineering", skills=("python",)),
        vacancy("HR Officer", "Human Resources", skills=("employee relations",)),
        vacancy("Head Performance Management", "Operations", skills=("performance management",)),
    ]
    evidence = CandidateEvidence(frozenset({"employee relations", "performance management"}), frozenset({"cv"}))
    result = run_employer_dry_run(employer="Heirs Holdings", vacancies=vacancies, evidence=evidence)
    assert result.status == DryRunStatus.READY
    assert result.selected is not None
    assert result.selected.job.title == "HR Officer"


def test_reports_evidence_gap_instead_of_inventing_claims():
    vacancies = [vacancy("HR Officer", "Human Resources", skills=("employee relations",), documents=("cv", "cover letter"))]
    evidence = CandidateEvidence(frozenset(), frozenset({"cv"}))
    result = run_employer_dry_run(employer="Heirs Holdings", vacancies=vacancies, evidence=evidence)
    assert result.status == DryRunStatus.EVIDENCE_GAP
    assert result.missing_skills == ("employee relations",)
    assert result.missing_documents == ("cover letter",)


def test_rejects_workflow_requesting_payment_or_financial_information():
    vacancies = [vacancy("HR Officer", "Human Resources", payment=True, financial=True)]
    evidence = CandidateEvidence(frozenset(), frozenset({"cv"}))
    result = run_employer_dry_run(employer="Heirs Holdings", vacancies=vacancies, evidence=evidence)
    assert result.status == DryRunStatus.UNSAFE_WORKFLOW


def test_engineering_only_portfolio_fails_closed():
    vacancies = [vacancy("Cloud Engineer", "Engineering")]
    evidence = CandidateEvidence(frozenset(), frozenset({"cv"}))
    result = run_employer_dry_run(employer="Heirs Holdings", vacancies=vacancies, evidence=evidence)
    assert result.status == DryRunStatus.NO_ELIGIBLE_TARGET

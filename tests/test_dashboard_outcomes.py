from core.dashboard import outcome_summary


def test_outcome_summary_surfaces_operational_states():
    summary = outcome_summary({"applied": 8, "retry_later": 2, "human_required": 1, "closed": 3, "failed": 4})
    assert "Confirmed:[/bold green] 8" in summary
    assert "Retry queue:[/bold yellow] 2" in summary
    assert "Human action:[/bold red] 1" in summary
    assert "Closed:[/bold] 3" in summary
    assert "Failed:[/bold] 4" in summary


def test_outcome_summary_defaults_missing_counts_to_zero():
    summary = outcome_summary({})
    assert summary.count(" 0") == 5

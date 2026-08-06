import json
from pathlib import Path

import pytest

from connectors.employer_registry import EmployerRegistry, EmployerRegistryError
from connectors.greenhouse import GreenhouseConnector


def write_registry(path: Path, employers: list[dict]) -> None:
    path.write_text(json.dumps({"schema_version": 1, "employers": employers}), encoding="utf-8")


def test_registry_is_fail_closed_and_canonical_is_blocked():
    registry = EmployerRegistry()
    approved = {board.board for board in registry.approved_boards()}
    blocked = {board.board for board in registry.blocked_boards()}
    assert "canonical" not in approved
    assert "canonical" in blocked
    assert approved == {"remotecom"}


def test_greenhouse_connector_fetches_only_approved_boards(monkeypatch, tmp_path: Path):
    registry_path = tmp_path / "employers.json"
    write_registry(
        registry_path,
        [
            {
                "company": "Blocked Co",
                "board": "blocked",
                "enabled": False,
                "automation_supported": True,
                "reason": "unsuitable",
                "role_focus": [],
            },
            {
                "company": "Approved Co",
                "board": "approved",
                "enabled": True,
                "automation_supported": True,
                "reason": "target roles",
                "role_focus": ["executive assistant"],
            },
        ],
    )
    requested: list[str] = []

    def fake_get_json(session, url):
        requested.append(url)
        return {
            "jobs": [
                {
                    "title": "Executive Assistant",
                    "absolute_url": "https://job-boards.greenhouse.io/approved/jobs/1",
                    "location": {"name": "Remote"},
                    "content": "Global role",
                },
                {
                    "title": "Software Engineer",
                    "absolute_url": "https://job-boards.greenhouse.io/approved/jobs/2",
                    "location": {"name": "Remote"},
                    "content": "Python",
                },
            ]
        }

    monkeypatch.setattr("connectors.greenhouse.get_json", fake_get_json)
    connector = GreenhouseConnector(EmployerRegistry(registry_path))
    jobs = list(connector.fetch_jobs())

    assert len(requested) == 1
    assert "/approved/" in requested[0]
    assert all("blocked" not in url for url in requested)
    assert [job.title for job in jobs] == ["Executive Assistant"]
    assert jobs[0].source == "Greenhouse:approved"
    assert connector.last_board_stats["Approved Co"]["fetched"] == 2
    assert connector.last_board_stats["Approved Co"]["admitted"] == 1


def test_invalid_registry_fails_closed(tmp_path: Path):
    path = tmp_path / "invalid.json"
    path.write_text('{"schema_version": 1, "employers": []}', encoding="utf-8")
    with pytest.raises(EmployerRegistryError):
        EmployerRegistry(path)

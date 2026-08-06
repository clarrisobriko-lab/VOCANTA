from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import json

from config.settings import GREENHOUSE_EMPLOYER_REGISTRY_FILE


class EmployerRegistryError(RuntimeError):
    """Raised when the employer registry is missing or invalid."""


@dataclass(frozen=True, slots=True)
class EmployerBoard:
    company: str
    board: str
    enabled: bool
    reason: str
    role_focus: tuple[str, ...]
    international_hiring: str
    sponsorship: str
    automation_supported: bool

    @property
    def is_approved(self) -> bool:
        return self.enabled and self.automation_supported


class EmployerRegistry:
    """Fail-closed registry for employer-level ATS discovery.

    Greenhouse is an ATS platform, not a single job source. VOCANTA therefore
    discovers only employer boards explicitly approved in this registry.
    """

    def __init__(self, path: Path | None = None) -> None:
        self.path = Path(path or GREENHOUSE_EMPLOYER_REGISTRY_FILE)
        self._boards = self._load()

    def _load(self) -> tuple[EmployerBoard, ...]:
        if not self.path.exists():
            raise EmployerRegistryError(f"Employer registry not found: {self.path}")
        try:
            payload = json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise EmployerRegistryError(f"Unable to read employer registry: {exc}") from exc

        if payload.get("schema_version") != 1:
            raise EmployerRegistryError("Unsupported employer registry schema_version")
        raw_employers = payload.get("employers")
        if not isinstance(raw_employers, list) or not raw_employers:
            raise EmployerRegistryError("Employer registry must contain employers")

        boards: list[EmployerBoard] = []
        seen_boards: set[str] = set()
        for index, raw in enumerate(raw_employers, start=1):
            if not isinstance(raw, dict):
                raise EmployerRegistryError(f"Employer entry {index} must be an object")
            company = str(raw.get("company", "")).strip()
            board = str(raw.get("board", "")).strip().lower()
            enabled = raw.get("enabled")
            automation_supported = raw.get("automation_supported", True)
            if not company or not board:
                raise EmployerRegistryError(f"Employer entry {index} requires company and board")
            if not isinstance(enabled, bool) or not isinstance(automation_supported, bool):
                raise EmployerRegistryError(
                    f"Employer entry {index} requires boolean enabled and automation_supported"
                )
            if board in seen_boards:
                raise EmployerRegistryError(f"Duplicate Greenhouse board: {board}")
            seen_boards.add(board)
            role_focus_raw = raw.get("role_focus", [])
            if not isinstance(role_focus_raw, list):
                raise EmployerRegistryError(f"Employer entry {index} role_focus must be a list")
            role_focus = tuple(
                str(value).strip().lower() for value in role_focus_raw if str(value).strip()
            )
            boards.append(
                EmployerBoard(
                    company=company,
                    board=board,
                    enabled=enabled,
                    reason=str(raw.get("reason", "")).strip(),
                    role_focus=role_focus,
                    international_hiring=str(raw.get("international_hiring", "unknown")).strip().lower(),
                    sponsorship=str(raw.get("sponsorship", "unknown")).strip().lower(),
                    automation_supported=automation_supported,
                )
            )
        return tuple(boards)

    def all_boards(self) -> tuple[EmployerBoard, ...]:
        return self._boards

    def approved_boards(self) -> tuple[EmployerBoard, ...]:
        return tuple(board for board in self._boards if board.is_approved)

    def blocked_boards(self) -> tuple[EmployerBoard, ...]:
        return tuple(board for board in self._boards if not board.is_approved)

    def summary(self) -> dict[str, int]:
        approved = self.approved_boards()
        return {
            "configured": len(self._boards),
            "approved": len(approved),
            "blocked": len(self._boards) - len(approved),
        }

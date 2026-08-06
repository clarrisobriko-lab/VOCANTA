import json
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path

from config.settings import DATA_DIR


@dataclass(slots=True)
class FieldAudit:
    label: str
    intent: str
    required: bool
    action: str
    result: str
    value_source: str = "profile"


@dataclass(slots=True)
class ApplicationDiagnostics:
    application_id: str
    ats: str
    url: str
    fields_detected: int = 0
    required_fields: int = 0
    filled_automatically: int = 0
    required_manual: int = 0
    optional_skipped: int = 0
    cv_uploaded: bool = False
    cover_letter_uploaded: bool = False
    submitted: bool = False
    submission_verified: bool = False
    submission_evidence: str = ""
    blocked_reason: str = ""
    field_audit: list[FieldAudit] = field(default_factory=list)

    @property
    def completion(self) -> int:
        denominator = max(1, self.required_fields)
        completed = max(0, self.required_fields - self.required_manual)
        return min(100, round(completed * 100 / denominator))

    def save(self, directory: Path | None = None) -> Path:
        target = directory or (DATA_DIR / "automation_reports")
        target.mkdir(parents=True, exist_ok=True)
        path = target / f"{self.application_id}.json"
        payload = asdict(self)
        payload["completion"] = self.completion
        payload["generated_at"] = datetime.now(timezone.utc).isoformat()
        path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
        return path

    def summary(self) -> str:
        return (
            f"Application ID: {self.application_id}\n"
            f"Fields detected: {self.fields_detected}\n"
            f"Filled automatically: {self.filled_automatically}\n"
            f"Required manual: {self.required_manual}\n"
            f"Optional skipped: {self.optional_skipped}\n"
            f"CV uploaded: {'YES' if self.cv_uploaded else 'NO'}\n"
            f"Cover letter uploaded: {'YES' if self.cover_letter_uploaded else 'NO'}\n"
            f"Submitted: {'VERIFIED' if self.submission_verified else 'YES' if self.submitted else 'NO'}\n"
            f"Completion: {self.completion}%"
        )

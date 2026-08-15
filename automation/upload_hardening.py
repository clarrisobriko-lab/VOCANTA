from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True, slots=True)
class UploadPlan:
    kind: str
    path: str
    required: bool


def classify_upload_label(label: str) -> str:
    text = " ".join((label or "").lower().split())
    if any(term in text for term in ("cover letter", "covering letter", "motivation letter")):
        return "cover_letter"
    if any(term in text for term in ("certificate", "supporting", "additional document", "other document", "attachment")):
        return "supporting"
    if any(term in text for term in ("resume", "résumé", "cv", "curriculum vitae")):
        return "cv"
    return "cv"


def choose_upload(label: str, *, resume_path: str, cover_letter_path: str = "", supporting_document_path: str = "", required: bool = False) -> UploadPlan | None:
    kind = classify_upload_label(label)
    candidates = {
        "cv": resume_path,
        "cover_letter": cover_letter_path,
        "supporting": supporting_document_path,
    }
    path = candidates[kind]
    if not path and kind != "cv":
        return None
    if not path:
        return None
    return UploadPlan(kind, path, required)


def validate_upload_path(path: str) -> tuple[bool, str]:
    if not path:
        return False, "document path is empty"
    file = Path(path)
    if not file.is_file():
        return False, f"document does not exist: {path}"
    if file.stat().st_size <= 0:
        return False, f"document is empty: {path}"
    if file.suffix.lower() not in {".pdf", ".doc", ".docx", ".txt", ".rtf"}:
        return False, f"unsupported document type: {file.suffix}"
    return True, "ok"

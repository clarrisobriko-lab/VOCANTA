import json
import shutil
import zipfile
from dataclasses import dataclass
from pathlib import Path

from docx import Document
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer

from agents.scorer import ApplicationDecision
from automation.tailoring import TailoredDocuments, safe_name
from core.models import Job


@dataclass(frozen=True, slots=True)
class ApplicationPackage:
    folder: Path
    cv_pdf: Path
    cover_letter_pdf: Path
    supporting_documents: tuple[Path, ...]
    internal_manifest: Path
    archive: Path


def docx_to_searchable_pdf(source: Path, destination: Path) -> Path:
    """Render DOCX paragraph text to a searchable, ATS-safe PDF."""
    document = Document(source)
    styles = getSampleStyleSheet()
    story = []
    for paragraph in document.paragraphs:
        text = paragraph.text.strip()
        if not text:
            story.append(Spacer(1, 6))
            continue
        style = styles["Heading2"] if paragraph.style.name.startswith("Heading") else styles["BodyText"]
        story.append(Paragraph(text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;"), style))
        story.append(Spacer(1, 4))
    if not story:
        raise ValueError(f"Cannot create PDF from empty document: {source}")
    destination.parent.mkdir(parents=True, exist_ok=True)
    SimpleDocTemplate(str(destination), pagesize=A4, title=source.stem).build(story)
    if not destination.is_file() or destination.stat().st_size < 100:
        raise RuntimeError(f"PDF generation failed: {destination}")
    return destination


def build_application_package(job: Job, documents: TailoredDocuments, decision: ApplicationDecision) -> ApplicationPackage:
    """Create employer-facing PDFs plus a separate internal audit manifest."""
    folder = documents.folder / "application_package"
    if folder.exists():
        shutil.rmtree(folder)
    folder.mkdir(parents=True)

    prefix = f"{safe_name(job.company)}_{safe_name(job.title)}"
    cv_pdf = docx_to_searchable_pdf(documents.resume_path, folder / f"{prefix}_CV.pdf")
    cover_pdf = docx_to_searchable_pdf(documents.cover_letter_path, folder / f"{prefix}_Cover_Letter.pdf")

    support = []
    if documents.certificate_path and documents.certificate_path.is_file():
        target = folder / documents.certificate_path.name
        shutil.copy2(documents.certificate_path, target)
        support.append(target)

    manifest = folder / "INTERNAL_APPLICATION_INTELLIGENCE.json"
    manifest.write_text(json.dumps({
        "company": job.company,
        "title": job.title,
        "composite_score": decision.score,
        "base_score": decision.base_score,
        "ats_score": decision.ats_score,
        "should_apply": decision.should_apply,
        "matched_skills": list(decision.matched_skills),
        "missing_skills": list(decision.missing_skills),
        "decision_reason": decision.reason,
        "employer_files": [cv_pdf.name, cover_pdf.name] + [item.name for item in support],
    }, indent=2), encoding="utf-8")

    archive = documents.folder / f"{prefix}_Application_Package.zip"
    if archive.exists():
        archive.unlink()
    with zipfile.ZipFile(archive, "w", compression=zipfile.ZIP_DEFLATED) as bundle:
        bundle.write(cv_pdf, cv_pdf.name)
        bundle.write(cover_pdf, cover_pdf.name)
        for item in support:
            bundle.write(item, item.name)
    return ApplicationPackage(folder, cv_pdf, cover_pdf, tuple(support), manifest, archive)

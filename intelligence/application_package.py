from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path


STOPWORDS = {"and", "the", "with", "for", "that", "this", "from", "you", "your", "our", "are", "will", "have", "has", "job", "role", "work", "team", "years", "experience"}


@dataclass(frozen=True, slots=True)
class ApplicationPackage:
    tailored_cv: str
    cover_letter: str
    ats_keywords: tuple[str, ...]
    ats_score: int


def extract_keywords(job_description: str, limit: int = 18) -> tuple[str, ...]:
    words = re.findall(r"[A-Za-z][A-Za-z+.#/-]{2,}", job_description.lower())
    counts: dict[str, int] = {}
    for word in words:
        clean = word.strip("./-")
        if clean in STOPWORDS or len(clean) < 3:
            continue
        counts[clean] = counts.get(clean, 0) + 1
    ranked = sorted(counts, key=lambda item: (-counts[item], item))
    return tuple(ranked[:limit])


def ats_match_score(cv_text: str, keywords: tuple[str, ...]) -> int:
    if not keywords:
        return 100
    haystack = cv_text.lower()
    matched = sum(1 for keyword in keywords if keyword in haystack)
    return round((matched / len(keywords)) * 100)


def tailor_cv(base_cv: str, job_title: str, job_description: str) -> tuple[str, tuple[str, ...], int]:
    keywords = extract_keywords(job_description)
    present = [keyword for keyword in keywords if keyword in base_cv.lower()]
    headline = f"TARGET ROLE: {job_title.strip()}"
    alignment = "CORE ALIGNMENT: " + (", ".join(present) if present else "Relevant transferable experience")
    tailored = f"{headline}\n{alignment}\n\n{base_cv.strip()}\n"
    return tailored, keywords, ats_match_score(tailored, keywords)


def generate_cover_letter(candidate_name: str, company: str, job_title: str, tailored_cv: str, keywords: tuple[str, ...]) -> str:
    evidence = [keyword for keyword in keywords if keyword in tailored_cv.lower()][:6]
    strengths = ", ".join(evidence) if evidence else "relevant transferable experience"
    return (
        f"Dear Hiring Manager,\n\n"
        f"I am applying for the {job_title} position at {company}. My background aligns with the role's priorities, particularly {strengths}. "
        "I would bring disciplined coordination, clear communication, careful execution and a strong commitment to reliable delivery.\n\n"
        "I would welcome the opportunity to discuss how my experience can support your team and its objectives.\n\n"
        f"Kind regards,\n{candidate_name}\n"
    )


def build_application_package(candidate_name: str, company: str, job_title: str, job_description: str, base_cv: str) -> ApplicationPackage:
    tailored, keywords, score = tailor_cv(base_cv, job_title, job_description)
    letter = generate_cover_letter(candidate_name, company, job_title, tailored, keywords)
    return ApplicationPackage(tailored, letter, keywords, score)


def write_package(package: ApplicationPackage, output_dir: Path | str) -> dict[str, Path]:
    directory = Path(output_dir)
    directory.mkdir(parents=True, exist_ok=True)
    cv_path = directory / "tailored_cv.txt"
    letter_path = directory / "cover_letter.txt"
    keywords_path = directory / "ats_keywords.txt"
    cv_path.write_text(package.tailored_cv, encoding="utf-8")
    letter_path.write_text(package.cover_letter, encoding="utf-8")
    keywords_path.write_text("\n".join(package.ats_keywords), encoding="utf-8")
    return {"cv": cv_path, "cover_letter": letter_path, "keywords": keywords_path}

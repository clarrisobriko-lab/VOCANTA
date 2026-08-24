import re
from collections.abc import Iterable


NEGATION_PREFIXES = (
    "no ",
    "never ",
    "not ",
    "not only ",
    "not limited to ",
    "not restricted to ",
    "isn't ",
    "is not ",
    "are not ",
    "without being ",
)


def normalize_text(value: str | None) -> str:
    return " ".join((value or "").lower().split())


def sanitize_applicant_text(value: str | None) -> str:
    """Enforce dash free applicant facing prose."""
    text = value or ""
    text = re.sub(r"\s*[\u2013\u2014]\s*", ", ", text)
    text = re.sub(r"\s*-\s*", " ", text)
    text = re.sub(r"\s+,\s*", ", ", text)
    text = re.sub(r",\s*,+", ",", text)
    return re.sub(r"[ \t]{2,}", " ", text).strip()


def sanitize_user_filename(value: str | None, *, fallback: str = "document") -> str:
    """Return a clean employer facing filename stem with no underscores or dashes."""
    text = sanitize_applicant_text(value or "")
    text = text.replace("_", " ")
    text = re.sub(r"[^A-Za-z0-9 .()&,+]+", " ", text)
    text = re.sub(r"\s+", " ", text).strip(" .")
    return text[:120] or fallback


def has_forbidden_dashes(value: str | None) -> bool:
    return any(character in (value or "") for character in ("-", "\u2013", "\u2014"))


def has_forbidden_filename_separator(value: str | None) -> bool:
    return "_" in (value or "") or has_forbidden_dashes(value)


def _pattern(term: str) -> re.Pattern[str]:
    normalized = normalize_text(term)
    return re.compile(rf"(?<!\w){re.escape(normalized)}(?!\w)", re.IGNORECASE)


def is_negated(text: str, start: int) -> bool:
    prefix = normalize_text(text[max(0, start - 48):start])
    return any(prefix.endswith(item.strip()) for item in NEGATION_PREFIXES)


def matched_terms(
    text: str,
    terms: Iterable[str],
    *,
    ignore_negated: bool = True,
) -> tuple[str, ...]:
    normalized = normalize_text(text)
    matches: list[str] = []
    for term in terms:
        occurrences = tuple(_pattern(term).finditer(normalized))
        if not occurrences:
            continue
        if ignore_negated and all(is_negated(normalized, match.start()) for match in occurrences):
            continue
        matches.append(term)
    return tuple(matches)


def contains_term(text: str, term: str, *, ignore_negated: bool = True) -> bool:
    return bool(matched_terms(text, (term,), ignore_negated=ignore_negated))


def contains_any(text: str, terms: Iterable[str], *, ignore_negated: bool = True) -> bool:
    return bool(matched_terms(text, terms, ignore_negated=ignore_negated))

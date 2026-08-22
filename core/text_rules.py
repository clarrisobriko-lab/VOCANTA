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
    """Remove typographic dashes from applicant facing generated prose.

    VOCANTA deliberately avoids em and en dashes in CVs, cover letters and
    application answers. A spaced dash is treated as a clause separator and
    becomes a comma. Remaining dash characters are replaced with spaces so
    date ranges and compounds remain readable without introducing forbidden
    punctuation.
    """
    text = value or ""
    text = re.sub(r"\s*[\u2013\u2014]\s*", ", ", text)
    text = re.sub(r"\s*-\s*", " ", text)
    text = re.sub(r"\s+,\s*", ", ", text)
    text = re.sub(r",\s*,+", ",", text)
    return re.sub(r"[ \t]{2,}", " ", text).strip()


def has_forbidden_dashes(value: str | None) -> bool:
    return any(character in (value or "") for character in ("\u2013", "\u2014"))


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
        if ignore_negated and all(
            is_negated(normalized, match.start()) for match in occurrences
        ):
            continue
        matches.append(term)
    return tuple(matches)


def contains_term(text: str, term: str, *, ignore_negated: bool = True) -> bool:
    return bool(matched_terms(text, (term,), ignore_negated=ignore_negated))


def contains_any(
    text: str,
    terms: Iterable[str],
    *,
    ignore_negated: bool = True,
) -> bool:
    return bool(matched_terms(text, terms, ignore_negated=ignore_negated))

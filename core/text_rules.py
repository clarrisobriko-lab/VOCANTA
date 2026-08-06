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

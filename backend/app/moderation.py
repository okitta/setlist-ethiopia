"""Anti-harassment and anti-fabrication rules.

This module is the code-level expression of the policy in
docs/policies/anti-abuse-and-fabrication.md. It is deliberately conservative: it
*prevents* the most obvious abuse at write time and *records* everything else for
human curators, rather than trying to be a perfect automated moderator.

Two families of rules:

1. Harassment — free-text fields are screened for slurs / targeted-abuse patterns.
2. Fabrication — structured records are checked for physically impossible or
   duplicate data (future-dated shows, absurd dates, duplicate setlist positions).

Everything that cannot be decided automatically is routed to the report/curation
workflow instead of being silently accepted or rejected.
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass
from datetime import date

# A small, editable blocklist of harassing terms. In production this is loaded from
# a curated, localced list (Amharic + English + transliterations) managed by the
# moderation team — kept out of source so it can be updated without a deploy.
# The samples below are placeholders that demonstrate the matching behaviour.
_HARASSMENT_TERMS = {
    "kill yourself",
    "kys",
    "worthless scum",
}

# Patterns for targeted abuse that are independent of a specific word list.
_HARASSMENT_PATTERNS = [
    re.compile(r"\byou\s+should\s+die\b", re.IGNORECASE),
    re.compile(r"\bi\s+will\s+(find|hurt|kill)\s+you\b", re.IGNORECASE),
]


class ModerationError(Exception):
    """Raised when content violates an anti-abuse rule. Carries a machine-readable
    code and a human-friendly, non-accusatory message."""

    def __init__(self, code: str, message: str):
        self.code = code
        self.message = message
        super().__init__(message)


def _normalise(text: str) -> str:
    # Fold accents / homoglyph tricks and collapse whitespace so simple evasion
    # (e.g. "k y s", extra spacing) does not bypass the check.
    folded = unicodedata.normalize("NFKD", text).casefold()
    return re.sub(r"\s+", " ", folded).strip()


def screen_text(text: str | None, *, field: str) -> None:
    """Reject free text that contains harassment. No-op for empty text."""
    if not text:
        return
    normalised = _normalise(text)
    for term in _HARASSMENT_TERMS:
        if term in normalised:
            raise ModerationError(
                code="harassment_blocked",
                message=(
                    f"The {field} appears to contain harassing language. "
                    "Please revise it. Repeated abuse may lead to account review."
                ),
            )
    collapsed = normalised.replace(" ", "")
    if any(t.replace(" ", "") in collapsed for t in _HARASSMENT_TERMS):
        raise ModerationError(
            code="harassment_blocked",
            message=f"The {field} appears to contain harassing language. Please revise it.",
        )
    for pattern in _HARASSMENT_PATTERNS:
        if pattern.search(text):
            raise ModerationError(
                code="harassment_blocked",
                message=f"The {field} appears to contain a threat or targeted abuse.",
            )


@dataclass(frozen=True)
class PerformanceFacts:
    performed_on: date
    venue: str
    city: str


def check_performance_plausibility(
    facts: PerformanceFacts, *, today: date, earliest_year: int
) -> None:
    """Reject records that are physically impossible and therefore fabricated.

    We cannot document a concert that has not happened yet, nor one from before
    recorded live music in the region. These are cheap, high-signal guards; subtler
    fabrication is handled by duplicate detection + community reports + curation.
    """
    if facts.performed_on > today:
        raise ModerationError(
            code="future_performance",
            message="A performance date cannot be in the future.",
        )
    if facts.performed_on.year < earliest_year:
        raise ModerationError(
            code="implausible_date",
            message=f"A performance date before {earliest_year} is not accepted.",
        )
    if not facts.venue.strip() or not facts.city.strip():
        raise ModerationError(
            code="incomplete_record",
            message="A performance needs both a venue and a city.",
        )

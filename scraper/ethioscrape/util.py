"""Small, dependency-free helpers: slugs, script detection, date parsing."""

from __future__ import annotations

import re
import unicodedata
from datetime import datetime, timezone

# Ethiopic (Geʽez) Unicode blocks — used to detect Amharic/Tigrinya/Geʽez text.
_ETHIOPIC_RANGES = (
    (0x1200, 0x137F),  # Ethiopic
    (0x1380, 0x139F),  # Ethiopic Supplement
    (0x2D80, 0x2DDF),  # Ethiopic Extended
    (0xAB00, 0xAB2F),  # Ethiopic Extended-A
)


def slugify(value: str) -> str:
    """ASCII slug. Transliterates accents; drops non-ASCII (e.g. Ethiopic), so a
    fully-Ethiopic name falls back to a hash-free readable stub."""
    ascii_text = (
        unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode("ascii")
    )
    ascii_text = re.sub(r"[^\w\s-]", "", ascii_text).strip().casefold()
    slug = re.sub(r"[\s_-]+", "-", ascii_text).strip("-")
    return slug or "item"


def is_ethiopic(text: str) -> bool:
    return any(
        any(lo <= ord(ch) <= hi for lo, hi in _ETHIOPIC_RANGES) for ch in text
    )


def guess_language_script(text: str) -> tuple[str | None, str | None]:
    """Return (language, script) best-guesses for a name string.

    We only assert what we can detect cheaply: Ethiopic script implies Amharic
    (`am` / `Ethi`); Latin implies `Latn` with unknown language (None)."""
    if is_ethiopic(text):
        return "am", "Ethi"
    if text.isascii():
        return None, "Latn"
    return None, None


def to_utc(dt: datetime) -> datetime:
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def parse_setlistfm_date(value: str) -> datetime | None:
    """setlist.fm eventDate is 'dd-MM-yyyy'."""
    try:
        return to_utc(datetime.strptime(value, "%d-%m-%Y"))
    except (ValueError, TypeError):
        return None


def parse_iso_date(value: str) -> datetime | None:
    """Parse an ISO 8601 date/datetime (schema.org startDate). Tolerates a trailing Z
    and date-only values."""
    if not value:
        return None
    raw = value.strip().replace("Z", "+00:00")
    for candidate in (raw, raw[:10]):
        try:
            return to_utc(datetime.fromisoformat(candidate))
        except ValueError:
            continue
    return None

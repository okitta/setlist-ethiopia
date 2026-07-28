"""Small, dependency-free helpers: slugs, script detection, date parsing."""

from __future__ import annotations

import hashlib
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
    """ASCII slug. Transliterates accents and drops non-ASCII characters. When a name
    has no ASCII content (e.g. a purely Ethiopic name), fall back to a short, stable
    hash of the original so distinct names get distinct slugs instead of all
    collapsing to one value (which would collide on the unique slug index)."""
    ascii_text = (
        unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode("ascii")
    )
    ascii_text = re.sub(r"[^\w\s-]", "", ascii_text).strip().casefold()
    slug = re.sub(r"[\s_-]+", "-", ascii_text).strip("-")
    if slug:
        return slug
    digest = hashlib.sha1(value.strip().encode("utf-8")).hexdigest()[:12]
    return f"x-{digest}"


def normalize_name(value: str) -> str:
    """Canonical identity key used by the app: trim, collapse internal whitespace,
    lowercase. Mirrors the deployed schema's
    lower(regexp_replace(trim(name), '\\s+', ' ', 'g')). Unicode-preserving, so
    Amharic text is kept (it simply has no case distinction)."""
    return " ".join(value.split()).lower()


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

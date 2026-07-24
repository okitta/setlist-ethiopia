"""Normalised, source-agnostic records + an in-memory `Dataset` that de-duplicates
across sources by slug before anything is written.

These mirror the canonical schema (artists, artist_names, venues, events,
performances, setlist_items) but are plain dataclasses so sources never touch the
database directly.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime


@dataclass
class Name:
    name: str
    language: str | None = None
    script: str | None = None
    kind: str = "alias"  # alias | legal | native | search-hint


@dataclass
class Artist:
    slug: str
    display_name: str
    native_name: str | None = None
    genre: str | None = None
    status: str = "community"
    names: list[Name] = field(default_factory=list)
    mbid: str | None = None  # kept for cross-source linking; not stored in DB

    def merge(self, other: "Artist") -> None:
        self.native_name = self.native_name or other.native_name
        self.genre = self.genre or other.genre
        self.mbid = self.mbid or other.mbid
        seen = {(n.name, n.kind) for n in self.names}
        for n in other.names:
            if (n.name, n.kind) not in seen:
                self.names.append(n)
                seen.add((n.name, n.kind))


@dataclass
class Venue:
    slug: str
    display_name: str
    city: str
    country: str = "Ethiopia"
    native_name: str | None = None
    address: str | None = None


@dataclass
class SetlistItem:
    position: int
    title: str
    section: str = "main"
    note: str | None = None
    confidence: str = "community"


@dataclass
class Performance:
    performance_date: datetime
    artist_slug: str | None = None
    submitted_artist: str | None = None
    submitted_venue: str | None = None
    event_slug: str | None = None
    status: str = "community"
    evidence: str | None = None  # source URL / provenance
    setlist: list[SetlistItem] = field(default_factory=list)

    def dedupe_key(self) -> tuple:
        return (
            self.artist_slug or self.submitted_artist,
            self.performance_date.date().isoformat(),
            self.event_slug or self.submitted_venue,
        )


@dataclass
class Event:
    slug: str
    title: str
    event_date: datetime
    venue_slug: str | None = None
    status: str = "announced"
    source_url: str | None = None


class Dataset:
    """Accumulates records from all sources, de-duplicating as it goes."""

    def __init__(self) -> None:
        self.artists: dict[str, Artist] = {}
        self.venues: dict[str, Venue] = {}
        self.events: dict[str, Event] = {}
        self.performances: list[Performance] = []
        self._perf_keys: set[tuple] = set()

    def add_artist(self, artist: Artist) -> None:
        existing = self.artists.get(artist.slug)
        if existing:
            existing.merge(artist)
        else:
            self.artists[artist.slug] = artist

    def add_venue(self, venue: Venue) -> None:
        self.venues.setdefault(venue.slug, venue)

    def add_event(self, event: Event) -> None:
        self.events.setdefault(event.slug, event)

    def add_performance(self, perf: Performance) -> None:
        key = perf.dedupe_key()
        if key in self._perf_keys:
            return
        self._perf_keys.add(key)
        self.performances.append(perf)

    def merge(self, other: "Dataset") -> None:
        for a in other.artists.values():
            self.add_artist(a)
        for v in other.venues.values():
            self.add_venue(v)
        for e in other.events.values():
            self.add_event(e)
        for p in other.performances:
            self.add_performance(p)

    def summary(self) -> dict[str, int]:
        return {
            "artists": len(self.artists),
            "artist_names": sum(len(a.names) for a in self.artists.values()),
            "venues": len(self.venues),
            "events": len(self.events),
            "performances": len(self.performances),
            "setlist_items": sum(len(p.setlist) for p in self.performances),
        }

    def to_dict(self) -> dict:
        def enc(obj):
            d = asdict(obj)
            for k, v in list(d.items()):
                if isinstance(v, datetime):
                    d[k] = v.isoformat()
            return d

        return {
            "artists": [enc(a) for a in self.artists.values()],
            "venues": [enc(v) for v in self.venues.values()],
            "events": [enc(e) for e in self.events.values()],
            "performances": [
                {
                    **{
                        k: (v.isoformat() if isinstance(v, datetime) else v)
                        for k, v in asdict(p).items()
                        if k != "setlist"
                    },
                    "setlist": [asdict(s) for s in p.setlist],
                }
                for p in self.performances
            ],
            "summary": self.summary(),
        }

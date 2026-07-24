"""setlist.fm source — real setlists become events + performances + setlist_items.

Requires a free API key (https://api.setlist.fm/docs/) supplied via SETLISTFM_API_KEY.
Given an artist's MusicBrainz id (from the musicbrainz source), we pull their setlists;
each setlist yields a venue, an event, a performance, and its ordered songs.
"""

from __future__ import annotations

from ..http import PoliteClient
from ..models import Dataset, Event, Performance, SetlistItem, Venue
from ..util import parse_setlistfm_date, slugify

SFM_BASE = "https://api.setlist.fm/rest/1.0"


def parse_setlist(doc: dict) -> tuple[Venue | None, Event | None, Performance | None]:
    """Convert one setlist.fm setlist object into normalised records."""
    date = parse_setlistfm_date(doc.get("eventDate", ""))
    if date is None:
        return None, None, None

    artist_name = (doc.get("artist") or {}).get("name")
    venue_doc = doc.get("venue") or {}
    venue_name = venue_doc.get("name")
    city_doc = venue_doc.get("city") or {}
    city = city_doc.get("name") or ""
    country = (city_doc.get("country") or {}).get("name") or "Ethiopia"

    venue = None
    venue_slug = None
    if venue_name:
        venue_slug = slugify(f"{venue_name}-{city}") if city else slugify(venue_name)
        venue = Venue(
            slug=venue_slug, display_name=venue_name, city=city or "Unknown", country=country
        )

    title = f"{artist_name} at {venue_name}" if artist_name and venue_name else (
        artist_name or venue_name or "Performance"
    )
    event_slug = slugify(f"{title}-{doc.get('eventDate', '')}")
    source_url = doc.get("url")
    event = Event(
        slug=event_slug,
        title=title,
        event_date=date,
        venue_slug=venue_slug,
        status="past",
        source_url=source_url,
    )

    items: list[SetlistItem] = []
    position = 1
    for set_block in (doc.get("sets") or {}).get("set", []):
        section = set_block.get("name") or ("encore" if set_block.get("encore") else "main")
        for song in set_block.get("song", []):
            name = (song.get("name") or "").strip()
            if not name:
                continue
            note = song.get("info")
            if song.get("cover"):
                cover = (song["cover"].get("name") or "").strip()
                note = f"cover of {cover}" if cover else note
            items.append(
                SetlistItem(position=position, title=name, section=section, note=note)
            )
            position += 1

    performance = Performance(
        performance_date=date,
        artist_slug=slugify(artist_name) if artist_name else None,
        submitted_artist=artist_name,
        submitted_venue=venue_name,
        event_slug=event_slug,
        status="community",
        evidence=source_url,
        setlist=items,
    )
    return venue, event, performance


def collect(
    client: PoliteClient,
    api_key: str,
    *,
    artist_mbids: list[str],
    max_pages: int = 2,
) -> Dataset:
    ds = Dataset()
    headers = {"Accept": "application/json", "x-api-key": api_key}
    for mbid in artist_mbids:
        for page in range(1, max_pages + 1):
            try:
                data = client.get_json(
                    f"{SFM_BASE}/artist/{mbid}/setlists",
                    headers=headers,
                    params={"p": page},
                )
            except RuntimeError:
                break  # 404 = artist has no setlists; move on
            setlists = data.get("setlist", [])
            if not setlists:
                break
            for sl in setlists:
                venue, event, perf = parse_setlist(sl)
                if venue:
                    ds.add_venue(venue)
                if event:
                    ds.add_event(event)
                if perf:
                    ds.add_performance(perf)
            if page * data.get("itemsPerPage", 20) >= data.get("total", 0):
                break
    return ds

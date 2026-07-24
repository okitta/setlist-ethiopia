"""Generic web scraper for event pages that embed schema.org JSON-LD.

Many venue/ticketing/listing pages include `<script type="application/ld+json">`
with a `MusicEvent` (or `Event`) object. This source fetches a caller-supplied list
of URLs (robots.txt respected), extracts those objects, and normalises them — a
genuine, portable scraping path that doesn't depend on any one site's HTML layout.
"""

from __future__ import annotations

import json

from bs4 import BeautifulSoup

from ..http import PoliteClient
from ..models import Dataset, Event, Performance, Venue
from ..util import parse_iso_date, slugify

_EVENT_TYPES = {"MusicEvent", "Event", "Festival", "TheaterEvent"}


def _iter_jsonld(html: str):
    soup = BeautifulSoup(html, "html.parser")
    for tag in soup.find_all("script", attrs={"type": "application/ld+json"}):
        raw = tag.string or tag.get_text() or ""
        if not raw.strip():
            continue
        try:
            data = json.loads(raw)
        except json.JSONDecodeError:
            continue
        # JSON-LD may be a single object, a list, or wrapped in @graph.
        if isinstance(data, dict) and "@graph" in data:
            yield from data["@graph"]
        elif isinstance(data, list):
            yield from data
        else:
            yield data


def _types(node: dict) -> set[str]:
    t = node.get("@type")
    if isinstance(t, list):
        return set(t)
    return {t} if t else set()


def _performers(node: dict) -> list[str]:
    performer = node.get("performer") or node.get("performers")
    out: list[str] = []
    if isinstance(performer, dict):
        performer = [performer]
    if isinstance(performer, list):
        for p in performer:
            if isinstance(p, dict) and p.get("name"):
                out.append(p["name"].strip())
            elif isinstance(p, str):
                out.append(p.strip())
    return out


def _location(node: dict) -> tuple[str | None, str, str, str | None]:
    """Return (venue_name, city, country, address)."""
    loc = node.get("location")
    if isinstance(loc, list):
        loc = loc[0] if loc else None
    if isinstance(loc, str):
        return loc.strip(), "", "Ethiopia", None
    if isinstance(loc, dict):
        name = (loc.get("name") or "").strip() or None
        addr = loc.get("address")
        city, country, address_str = "", "Ethiopia", None
        if isinstance(addr, dict):
            city = addr.get("addressLocality") or ""
            country = addr.get("addressCountry") or "Ethiopia"
            address_str = addr.get("streetAddress")
        elif isinstance(addr, str):
            address_str = addr
        return name, city, country, address_str
    return None, "", "Ethiopia", None


def parse_html(html: str, url: str) -> Dataset:
    ds = Dataset()
    for node in _iter_jsonld(html):
        if not isinstance(node, dict) or not (_types(node) & _EVENT_TYPES):
            continue
        date = parse_iso_date(node.get("startDate", ""))
        if date is None:
            continue
        title = (node.get("name") or "").strip() or "Event"
        venue_name, city, country, address = _location(node)

        venue_slug = None
        if venue_name:
            venue_slug = slugify(f"{venue_name}-{city}") if city else slugify(venue_name)
            ds.add_venue(
                Venue(
                    slug=venue_slug,
                    display_name=venue_name,
                    city=city or "Unknown",
                    country=country or "Ethiopia",
                    address=address,
                )
            )

        event_slug = slugify(f"{title}-{date.date().isoformat()}")
        ds.add_event(
            Event(
                slug=event_slug,
                title=title,
                event_date=date,
                venue_slug=venue_slug,
                status="announced",
                source_url=node.get("url") or url,
            )
        )

        performers = _performers(node) or [None]
        for name in performers:
            ds.add_performance(
                Performance(
                    performance_date=date,
                    artist_slug=slugify(name) if name else None,
                    submitted_artist=name,
                    submitted_venue=venue_name,
                    event_slug=event_slug,
                    status="community",
                    evidence=node.get("url") or url,
                )
            )
    return ds


def collect(client: PoliteClient, *, urls: list[str]) -> Dataset:
    ds = Dataset()
    for url in urls:
        url = url.strip()
        if not url or url.startswith("#"):
            continue
        try:
            html = client.get_text(url)
        except (RuntimeError, PermissionError) as exc:
            print(f"  ! skipped {url}: {exc}")
            continue
        ds.merge(parse_html(html, url))
    return ds

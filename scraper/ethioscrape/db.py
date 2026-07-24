"""Load a normalised `Dataset` into the canonical Postgres schema.

Design choices:
* **Upsert by slug** for artists/venues/events so re-runs don't duplicate.
* **Everything is community-status** with an evidence/source trail — scraped rows are
  suggestions for curators, never authoritative.
* We never insert users; `created_by`/`submitted_by` are left NULL.
* Postgres-only (uses `ON CONFLICT`). The canonical tables must already exist
  (docs/database/canonical_supabase_schema.sql).
"""

from __future__ import annotations

from sqlalchemy import (
    Column,
    DateTime,
    Integer,
    MetaData,
    Table,
    Text,
    create_engine,
    select,
)
from sqlalchemy.dialects.postgresql import insert as pg_insert

from .models import Dataset

metadata = MetaData()

artists = Table(
    "artists", metadata,
    Column("id", Integer, primary_key=True),
    Column("slug", Text), Column("display_name", Text), Column("native_name", Text),
    Column("genre", Text), Column("status", Text),
)
artist_names = Table(
    "artist_names", metadata,
    Column("id", Integer, primary_key=True),
    Column("artist_id", Integer), Column("name", Text),
    Column("language", Text), Column("script", Text), Column("kind", Text),
)
venues = Table(
    "venues", metadata,
    Column("id", Integer, primary_key=True),
    Column("slug", Text), Column("display_name", Text), Column("native_name", Text),
    Column("city", Text), Column("country", Text), Column("address", Text),
)
events = Table(
    "events", metadata,
    Column("id", Integer, primary_key=True),
    Column("slug", Text), Column("title", Text),
    Column("event_date", DateTime(timezone=True)), Column("venue_id", Integer),
    Column("status", Text), Column("source_url", Text),
)
performances = Table(
    "performances", metadata,
    Column("id", Integer, primary_key=True),
    Column("event_id", Integer), Column("artist_id", Integer),
    Column("submitted_artist", Text), Column("submitted_venue", Text),
    Column("performance_date", DateTime(timezone=True)),
    Column("status", Text), Column("evidence", Text),
)
setlist_items = Table(
    "setlist_items", metadata,
    Column("id", Integer, primary_key=True),
    Column("performance_id", Integer), Column("position", Integer),
    Column("title", Text), Column("section", Text), Column("note", Text),
    Column("confidence", Text),
)


class LoadStats(dict):
    """Counts of rows inserted/updated per table."""


def _normalise_url(url: str) -> str:
    """Pin the psycopg (v3) driver so a plain Supabase `postgresql://` URL works
    without psycopg2 installed. Rejects non-Postgres URLs with a clear message —
    the usual mistake is pasting the Supabase project URL (https://<ref>.supabase.co)
    instead of the database connection string."""
    for prefix in ("postgres://", "postgresql://"):
        if url.startswith(prefix):
            return "postgresql+psycopg://" + url[len(prefix) :]
    if url.startswith("postgresql"):  # already has an explicit driver, e.g. +psycopg
        return url
    scheme = url.split("://", 1)[0] if "://" in url else url
    raise ValueError(
        f"database URL must be a Postgres connection string (postgresql://...), "
        f"but got scheme '{scheme}'. This looks like the Supabase project/API URL, "
        f"not the database URL. In Supabase open Connect → Session pooler and copy "
        f"the URI (host aws-0-<region>.pooler.supabase.com, port 5432, db 'postgres'), "
        f"replacing [YOUR-PASSWORD]."
    )


def load(dataset: Dataset, database_url: str) -> LoadStats:
    engine = create_engine(_normalise_url(database_url), future=True)
    stats = LoadStats(
        artists=0, artist_names=0, venues=0, events=0, performances=0, setlist_items=0
    )
    with engine.begin() as conn:
        artist_ids: dict[str, int] = {}
        venue_ids: dict[str, int] = {}
        event_ids: dict[str, int] = {}

        # --- artists (+ names) --------------------------------------------
        for a in dataset.artists.values():
            stmt = (
                pg_insert(artists)
                .values(
                    slug=a.slug, display_name=a.display_name,
                    native_name=a.native_name, genre=a.genre, status=a.status,
                )
                .on_conflict_do_update(
                    index_elements=["slug"],
                    set_={"native_name": a.native_name, "genre": a.genre},
                )
                .returning(artists.c.id)
            )
            aid = conn.execute(stmt).scalar_one()
            artist_ids[a.slug] = aid
            stats["artists"] += 1

            existing = {
                r[0]
                for r in conn.execute(
                    select(artist_names.c.name).where(artist_names.c.artist_id == aid)
                )
            }
            for n in a.names:
                if n.name in existing:
                    continue
                conn.execute(
                    artist_names.insert().values(
                        artist_id=aid, name=n.name, language=n.language,
                        script=n.script, kind=n.kind,
                    )
                )
                existing.add(n.name)
                stats["artist_names"] += 1

        # --- venues -------------------------------------------------------
        for v in dataset.venues.values():
            stmt = (
                pg_insert(venues)
                .values(
                    slug=v.slug, display_name=v.display_name, native_name=v.native_name,
                    city=v.city, country=v.country, address=v.address,
                )
                .on_conflict_do_update(
                    index_elements=["slug"], set_={"address": v.address}
                )
                .returning(venues.c.id)
            )
            venue_ids[v.slug] = conn.execute(stmt).scalar_one()
            stats["venues"] += 1

        # --- events -------------------------------------------------------
        for e in dataset.events.values():
            stmt = (
                pg_insert(events)
                .values(
                    slug=e.slug, title=e.title, event_date=e.event_date,
                    venue_id=venue_ids.get(e.venue_slug), status=e.status,
                    source_url=e.source_url,
                )
                .on_conflict_do_update(
                    index_elements=["slug"],
                    set_={"venue_id": venue_ids.get(e.venue_slug)},
                )
                .returning(events.c.id)
            )
            event_ids[e.slug] = conn.execute(stmt).scalar_one()
            stats["events"] += 1

        # --- performances (+ setlist items) -------------------------------
        for p in dataset.performances:
            artist_id = artist_ids.get(p.artist_slug) if p.artist_slug else None
            event_id = event_ids.get(p.event_slug) if p.event_slug else None

            # performances has no unique constraint; guard against re-run dupes.
            dupe = conn.execute(
                select(performances.c.id).where(
                    performances.c.performance_date == p.performance_date,
                    performances.c.submitted_artist == p.submitted_artist,
                    performances.c.submitted_venue == p.submitted_venue,
                )
            ).first()
            if dupe:
                continue

            pid = conn.execute(
                performances.insert()
                .values(
                    event_id=event_id, artist_id=artist_id,
                    submitted_artist=p.submitted_artist,
                    submitted_venue=p.submitted_venue,
                    performance_date=p.performance_date,
                    status=p.status, evidence=p.evidence,
                )
                .returning(performances.c.id)
            ).scalar_one()
            stats["performances"] += 1

            for item in p.setlist:
                conn.execute(
                    setlist_items.insert().values(
                        performance_id=pid, position=item.position, title=item.title,
                        section=item.section, note=item.note, confidence=item.confidence,
                    )
                )
                stats["setlist_items"] += 1

    return stats

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

import hashlib

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
from sqlalchemy.exc import OperationalError

from .models import Dataset
from .util import normalize_name

metadata = MetaData()

artists = Table(
    "artists", metadata,
    Column("id", Integer, primary_key=True),
    Column("slug", Text), Column("display_name", Text), Column("native_name", Text),
    Column("normalized_name", Text), Column("description", Text),
    Column("genre", Text), Column("status", Text),
)
artist_names = Table(
    "artist_names", metadata,
    Column("id", Integer, primary_key=True),
    Column("artist_id", Integer), Column("name", Text),
    Column("normalized_name", Text),
    Column("language", Text), Column("script", Text), Column("kind", Text),
)
venues = Table(
    "venues", metadata,
    Column("id", Integer, primary_key=True),
    Column("slug", Text), Column("display_name", Text), Column("native_name", Text),
    Column("normalized_name", Text),
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


def _unique_slug(conn, table: Table, slug: str, seed: str) -> str:
    """Return `slug` if free, otherwise a disambiguated variant. Guards the unique
    slug index when two distinct records would otherwise produce the same slug."""
    if conn.execute(select(table.c.id).where(table.c.slug == slug)).first() is None:
        return slug
    return f"{slug}-{hashlib.sha1(seed.encode('utf-8')).hexdigest()[:6]}"


def load(dataset: Dataset, database_url: str) -> LoadStats:
    engine = create_engine(_normalise_url(database_url), future=True)

    # Preflight: turn an unreachable-server failure into an actionable message. The
    # usual cause from CI is Supabase's IPv6-only Direct connection on an IPv4-only
    # runner — the Session pooler (IPv4) is what to use there.
    try:
        with engine.connect():
            pass
    except OperationalError as exc:
        raise RuntimeError(
            "Could not connect to Postgres. From GitHub Actions (or any IPv4-only "
            "host), use Supabase's Session pooler URI — host "
            "aws-0-<region>.pooler.supabase.com, port 5432. The Direct connection "
            "(db.<ref>.supabase.co) is IPv6-only and unreachable from IPv4 runners.\n"
            f"Original error: {exc.orig}"
        ) from exc

    stats = LoadStats(
        artists=0, artist_names=0, venues=0, events=0, performances=0, setlist_items=0
    )
    with engine.begin() as conn:
        artist_ids: dict[str, int] = {}
        venue_ids: dict[str, int] = {}
        event_ids: dict[str, int] = {}

        # --- artists (+ names) --------------------------------------------
        # Dedup by normalized_name (the app's identity key), which also populates the
        # required normalized_name column. Slug is disambiguated if already taken.
        for a in dataset.artists.values():
            norm = normalize_name(a.display_name)
            existing_id = conn.execute(
                select(artists.c.id).where(artists.c.normalized_name == norm)
            ).scalar()
            if existing_id is not None:
                aid = existing_id
                # Enrich only; never clobber curated fields with a blank.
                conn.execute(
                    artists.update()
                    .where(artists.c.id == aid)
                    .values(native_name=a.native_name, genre=a.genre)
                )
            else:
                aid = conn.execute(
                    artists.insert()
                    .values(
                        slug=_unique_slug(conn, artists, a.slug, norm),
                        display_name=a.display_name,
                        normalized_name=norm,
                        native_name=a.native_name,
                        genre=a.genre,
                        status=a.status,
                    )
                    .returning(artists.c.id)
                ).scalar_one()
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
                        artist_id=aid, name=n.name, normalized_name=normalize_name(n.name),
                        language=n.language, script=n.script, kind=n.kind,
                    )
                )
                existing.add(n.name)
                stats["artist_names"] += 1

        # --- venues -------------------------------------------------------
        for v in dataset.venues.values():
            norm = normalize_name(v.display_name)
            existing_id = conn.execute(
                select(venues.c.id).where(venues.c.normalized_name == norm)
            ).scalar()
            if existing_id is not None:
                vid = existing_id
                conn.execute(
                    venues.update().where(venues.c.id == vid).values(address=v.address)
                )
            else:
                vid = conn.execute(
                    venues.insert()
                    .values(
                        slug=_unique_slug(conn, venues, v.slug, norm),
                        display_name=v.display_name,
                        normalized_name=norm,
                        native_name=v.native_name,
                        city=v.city,
                        country=v.country,
                        address=v.address,
                    )
                    .returning(venues.c.id)
                ).scalar_one()
            venue_ids[v.slug] = vid
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

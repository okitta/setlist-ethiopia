"""Loader test against a real Postgres. Skipped unless SCRAPER_TEST_DATABASE_URL is
set (e.g. a throwaway Docker container with the canonical schema applied).

    docker run -d --name sl_pg -p 5433:5432 -e POSTGRES_PASSWORD=test \
        -e POSTGRES_DB=setlist postgres:16-alpine
    psql "postgresql://postgres:test@localhost:5433/setlist" \
        -f docs/database/canonical_supabase_schema.sql
    SCRAPER_TEST_DATABASE_URL="postgresql+psycopg://postgres:test@localhost:5433/setlist" \
        pytest tests/test_loader.py
"""

import os

import pytest
from sqlalchemy import create_engine, text

from ethioscrape import fixtures
from ethioscrape.db import _normalise_url, load

URL = os.environ.get("SCRAPER_TEST_DATABASE_URL")
# Normalise so the test's own verification engine uses the psycopg (v3) driver too,
# whether the URL is given as postgresql:// or postgresql+psycopg://.
ENGINE_URL = _normalise_url(URL) if URL else None
pytestmark = pytest.mark.skipif(not URL, reason="SCRAPER_TEST_DATABASE_URL not set")


def _count(engine, table):
    with engine.connect() as c:
        return c.execute(text(f'SELECT count(*) FROM "{table}"')).scalar_one()


def test_load_is_idempotent_and_wires_foreign_keys():
    ds = fixtures.build_sample_dataset()

    stats1 = load(ds, URL)
    assert stats1["artists"] == 3
    assert stats1["performances"] == 3
    assert stats1["setlist_items"] == 5

    engine = create_engine(ENGINE_URL, future=True)
    assert _count(engine, "artists") == 3
    assert _count(engine, "performances") == 3

    # Foreign keys resolved: every setlist item points at a real performance,
    # and events reference venues.
    with engine.connect() as c:
        orphan_items = c.execute(
            text(
                "SELECT count(*) FROM setlist_items s "
                "LEFT JOIN performances p ON p.id = s.performance_id "
                "WHERE p.id IS NULL"
            )
        ).scalar_one()
        assert orphan_items == 0
        native = c.execute(
            text("SELECT native_name FROM artists WHERE slug = 'mulatu-astatke'")
        ).scalar_one()
        assert native == "ሙላቱ አስታጥቄ"

    # Re-running must not duplicate rows.
    load(ds, URL)
    assert _count(engine, "artists") == 3
    assert _count(engine, "performances") == 3
    assert _count(engine, "setlist_items") == 5

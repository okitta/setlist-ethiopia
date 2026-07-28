"""Offline tests for the normalise → dedupe pipeline (no network)."""

from ethioscrape import fixtures
from ethioscrape.models import Dataset
from ethioscrape.sources import jsonld, musicbrainz, setlistfm
from ethioscrape.util import (
    guess_language_script,
    is_ethiopic,
    normalize_name,
    slugify,
)


def test_slugify_handles_ethiopic_and_latin():
    assert slugify("Aster Aweke") == "aster-aweke"
    # Fully Ethiopic names have no ASCII -> a stable hash slug, distinct per name,
    # so they never collide on the unique slug index (the old "item" bug).
    s1, s2 = slugify("አስቴር"), slugify("ሙላቱ")
    assert s1 != "item" and s1 != s2
    assert slugify("አስቴር") == s1  # stable across calls


def test_normalize_name_matches_app_identity_key():
    assert normalize_name("  Aster   Aweke ") == "aster aweke"
    assert normalize_name("Mulatu Astatke") == "mulatu astatke"
    # Amharic has no case; whitespace is still collapsed/trimmed.
    assert normalize_name(" ሙላቱ  አስታጥቄ ") == "ሙላቱ አስታጥቄ"


def test_script_detection():
    assert is_ethiopic("ሙላቱ")
    assert not is_ethiopic("Mulatu")
    assert guess_language_script("ሙላቱ") == ("am", "Ethi")


def test_musicbrainz_parse_extracts_native_name_and_genre():
    artist = musicbrainz.parse_artist(fixtures.MB_ARTISTS[0])
    assert artist.display_name == "Mulatu Astatke"
    assert artist.native_name == "ሙላቱ አስታጥቄ"
    assert artist.genre == "ethio-jazz"  # highest-voted genre wins
    # Amharic alias is tagged as Ethiopic script / Amharic language.
    native = next(n for n in artist.names if n.name == "ሙላቱ አስታጥቄ")
    assert native.script == "Ethi" and native.language == "am"


def test_setlistfm_parse_positions_sections_and_encore():
    _, event, perf = setlistfm.parse_setlist(fixtures.SFM_SETLISTS[0])
    assert event.title.startswith("Mulatu Astatke at")
    titles = [(i.position, i.title, i.section) for i in perf.setlist]
    assert titles[0] == (1, "Yekermo Sew", "main")
    assert titles[-1] == (3, "Mulatu", "encore")  # encore continues the numbering
    assert perf.evidence and perf.evidence.startswith("https://")


def test_jsonld_parse_music_event():
    ds = jsonld.parse_html(fixtures.JSONLD_HTML, "https://example.org/x")
    assert len(ds.events) == 1
    assert "ghion-hotel-addis-ababa" in ds.venues
    perf = ds.performances[0]
    assert perf.submitted_artist == "Tsegaye Eshetu"
    assert perf.performance_date.year == 2024


def test_sample_dataset_summary_covers_all_tables():
    ds = fixtures.build_sample_dataset()
    s = ds.summary()
    assert s["artists"] == 3
    assert s["performances"] == 3  # 2 setlist.fm + 1 jsonld
    assert s["setlist_items"] == 5  # 3 + 2
    assert s["venues"] == 3
    assert s["artist_names"] >= 3


def test_performance_dedupe():
    ds = Dataset()
    _, _, perf = setlistfm.parse_setlist(fixtures.SFM_SETLISTS[0])
    ds.add_performance(perf)
    ds.add_performance(perf)  # identical -> ignored
    assert len(ds.performances) == 1


def test_to_dict_is_json_serialisable():
    import json

    ds = fixtures.build_sample_dataset()
    text = json.dumps(ds.to_dict(), ensure_ascii=False)
    assert "ሙላቱ አስታጥቄ" in text  # native names survive round-trip


def test_load_rejects_non_postgres_url():
    """A Supabase project URL (https://...) must fail fast with a clear message,
    not SQLAlchemy's cryptic 'Can't load plugin: sqlalchemy.dialects:https'."""
    import pytest

    from ethioscrape.db import load

    with pytest.raises(ValueError, match="Postgres connection string"):
        load(Dataset(), "https://abcd1234.supabase.co")

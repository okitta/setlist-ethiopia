"""Realistic sample payloads mirroring each source's real API/HTML shape.

Used by `--sample` (offline demo) and by the tests, so the whole
normalise → dedupe → load pipeline can be exercised without any network access or
API keys. Artists span secular (ethio-jazz, pop) and gospel to reflect the brief.
"""

from __future__ import annotations

from .models import Dataset
from .sources import jsonld, musicbrainz, setlistfm

# --- MusicBrainz artist lookup documents ----------------------------------
MB_ARTISTS = [
    {
        "id": "mbid-mulatu",
        "name": "Mulatu Astatke",
        "genres": [{"name": "ethio-jazz", "count": 12}, {"name": "jazz", "count": 5}],
        "aliases": [
            {"name": "ሙላቱ አስታጥቄ", "locale": "am", "type": "Artist name"},
            {"name": "Mulatu Astatqe", "type": "Search hint"},
        ],
    },
    {
        "id": "mbid-aster",
        "name": "Aster Aweke",
        "genres": [{"name": "ethiopian pop", "count": 8}],
        "aliases": [{"name": "አስቴር አወቀ", "locale": "am", "type": "Artist name"}],
    },
    {
        "id": "mbid-tsegaye",
        "name": "Tsegaye Eshetu",
        "genres": [{"name": "gospel", "count": 4}],
        "aliases": [{"name": "ጸጋዬ እሸቱ", "locale": "am", "type": "Artist name"}],
    },
]

# --- setlist.fm setlist objects -------------------------------------------
SFM_SETLISTS = [
    {
        "eventDate": "02-03-2019",
        "url": "https://www.setlist.fm/setlist/mulatu/2019/example.html",
        "artist": {"name": "Mulatu Astatke"},
        "venue": {
            "name": "African Jazz Village",
            "city": {"name": "Addis Ababa", "country": {"name": "Ethiopia"}},
        },
        "sets": {
            "set": [
                {"song": [{"name": "Yekermo Sew"}, {"name": "Tezeta"}]},
                {"encore": 1, "song": [{"name": "Mulatu"}]},
            ]
        },
    },
    {
        "eventDate": "15-09-2018",
        "url": "https://www.setlist.fm/setlist/aster/2018/example.html",
        "artist": {"name": "Aster Aweke"},
        "venue": {
            "name": "Millennium Hall",
            "city": {"name": "Addis Ababa", "country": {"name": "Ethiopia"}},
        },
        "sets": {"set": [{"song": [{"name": "Tchuhet"}, {"name": "Abebayehosh"}]}]},
    },
]

# --- A page embedding schema.org JSON-LD (gospel concert) ------------------
JSONLD_HTML = """
<!doctype html><html><head>
<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "MusicEvent",
  "name": "Gospel Praise Night",
  "startDate": "2024-12-20T19:00:00+03:00",
  "url": "https://example.org/events/gospel-praise-night",
  "performer": [{"@type": "MusicGroup", "name": "Tsegaye Eshetu"}],
  "location": {
    "@type": "Place",
    "name": "Ghion Hotel",
    "address": {"@type": "PostalAddress", "addressLocality": "Addis Ababa",
                "addressCountry": "Ethiopia", "streetAddress": "Ras Desta Damtew Ave"}
  }
}
</script></head><body></body></html>
"""


def build_sample_dataset() -> Dataset:
    ds = Dataset()
    for doc in MB_ARTISTS:
        ds.add_artist(musicbrainz.parse_artist(doc))
    for sl in SFM_SETLISTS:
        venue, event, perf = setlistfm.parse_setlist(sl)
        if venue:
            ds.add_venue(venue)
        if event:
            ds.add_event(event)
        if perf:
            ds.add_performance(perf)
    ds.merge(jsonld.parse_html(JSONLD_HTML, "https://example.org/events/gospel-praise-night"))
    return ds

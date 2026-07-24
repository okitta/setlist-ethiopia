"""MusicBrainz source — discover Ethiopian artists and their names/genre.

MusicBrainz data is open (CC0) and has a documented API. We use it to *discover*
artists (by area = Ethiopia, plus optional genre queries so gospel/other artists can
be targeted) and to pull aliases — which give us native Amharic names for
`artist_names`.

API etiquette (enforced by PoliteClient): a descriptive User-Agent and <=1 req/sec.
"""

from __future__ import annotations

from ..http import PoliteClient
from ..models import Artist, Dataset, Name
from ..util import guess_language_script, is_ethiopic, slugify

MB_BASE = "https://musicbrainz.org/ws/2"


def parse_artist(doc: dict) -> Artist:
    """Turn a MusicBrainz artist lookup document into a normalised Artist."""
    display = doc.get("name", "").strip()
    slug = slugify(display) if display else slugify(doc.get("id", "artist"))

    names: list[Name] = []
    native_name: str | None = None
    if is_ethiopic(display):
        native_name = display
    for alias in doc.get("aliases") or []:
        alias_name = (alias.get("name") or "").strip()
        if not alias_name:
            continue
        locale = alias.get("locale")
        _, script = guess_language_script(alias_name)
        language = locale or (_ if _ else None)
        kind = "legal" if alias.get("type") == "Legal name" else "alias"
        names.append(Name(name=alias_name, language=language, script=script, kind=kind))
        if native_name is None and is_ethiopic(alias_name):
            native_name = alias_name

    # Prefer explicit `genres` (voted), fall back to top `tags`.
    genre = None
    genres = sorted(
        doc.get("genres") or [], key=lambda g: g.get("count", 0), reverse=True
    )
    if genres:
        genre = genres[0].get("name")
    elif doc.get("tags"):
        top = sorted(doc["tags"], key=lambda t: t.get("count", 0), reverse=True)
        genre = top[0].get("name") if top else None

    artist = Artist(
        slug=slug,
        display_name=display,
        native_name=native_name,
        genre=genre,
        names=names,
        mbid=doc.get("id"),
    )
    # Record the primary display name too (helps search/native coverage).
    lang, script = guess_language_script(display)
    artist.names.insert(0, Name(name=display, language=lang, script=script, kind="primary"))
    return artist


def collect(
    client: PoliteClient,
    *,
    area: str = "Ethiopia",
    queries: list[str] | None = None,
    limit: int = 50,
) -> Dataset:
    """Search MusicBrainz for artists and look each up for aliases/genre."""
    ds = Dataset()
    search_terms = [f"area:{area}"] + list(queries or [])
    seen_ids: set[str] = set()

    for term in search_terms:
        offset = 0
        while len(seen_ids) < limit:
            page = client.get_json(
                f"{MB_BASE}/artist",
                headers={"Accept": "application/json"},
                params={"query": term, "fmt": "json", "limit": 100, "offset": offset},
                check_robots=False,  # documented API, not a crawlable page
            )
            hits = page.get("artists", [])
            if not hits:
                break
            for hit in hits:
                mbid = hit.get("id")
                if not mbid or mbid in seen_ids:
                    continue
                seen_ids.add(mbid)
                doc = client.get_json(
                    f"{MB_BASE}/artist/{mbid}",
                    headers={"Accept": "application/json"},
                    params={"fmt": "json", "inc": "aliases+genres+tags"},
                    check_robots=False,  # documented API, not a crawlable page
                )
                ds.add_artist(parse_artist(doc))
                if len(seen_ids) >= limit:
                    break
            offset += 100
            if offset >= page.get("count", 0):
                break
    return ds

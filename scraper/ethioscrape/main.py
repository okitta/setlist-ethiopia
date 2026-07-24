"""Command-line entry point.

Examples
--------
Offline demo (no network, no keys) — writes reviewable JSON:
    python -m ethioscrape.main --sample --out out/sample.json

Discover Ethiopian artists from MusicBrainz + their setlists, write JSON:
    SETLISTFM_API_KEY=xxx python -m ethioscrape.main \
        --sources musicbrainz,setlistfm --limit 50 --out out/data.json

Scrape event pages that embed schema.org JSON-LD:
    python -m ethioscrape.main --sources jsonld --urls-file urls.txt

Load straight into Postgres/Supabase (canonical schema must already exist):
    python -m ethioscrape.main --sample --database-url "$SUPABASE_DB_URL"
"""

from __future__ import annotations

import argparse
import json
import os
import pathlib
import sys

from .http import PoliteClient
from .models import Dataset


def _run_sources(args) -> Dataset:
    from .sources import jsonld, musicbrainz, setlistfm

    ds = Dataset()
    client = PoliteClient(
        contact=args.contact, min_interval=args.min_interval, obey_robots=not args.ignore_robots
    )
    selected = [s.strip() for s in args.sources.split(",") if s.strip()]

    if "musicbrainz" in selected:
        print(f"→ MusicBrainz: discovering artists (area={args.area}, limit={args.limit})")
        mb = musicbrainz.collect(
            client, area=args.area, queries=args.query, limit=args.limit
        )
        ds.merge(mb)
        print(f"  found {len(mb.artists)} artists")

    if "setlistfm" in selected:
        api_key = os.environ.get("SETLISTFM_API_KEY")
        if not api_key:
            print("  ! SETLISTFM_API_KEY not set — skipping setlist.fm", file=sys.stderr)
        else:
            from .budget import DailyBudget

            budget = DailyBudget(args.budget_file, args.setlistfm_daily_budget)
            mbids = [a.mbid for a in ds.artists.values() if a.mbid]
            print(
                f"→ setlist.fm: fetching setlists for {len(mbids)} artists "
                f"(daily budget {budget.remaining}/{budget.limit} left)"
            )
            sfm = setlistfm.collect(
                client, api_key, artist_mbids=mbids, max_pages=args.max_pages, budget=budget
            )
            ds.merge(sfm)
            print(
                f"  found {len(sfm.performances)} performances "
                f"(used {budget.used}/{budget.limit} today)"
            )

    if "jsonld" in selected:
        urls: list[str] = []
        if args.urls_file:
            urls = pathlib.Path(args.urls_file).read_text(encoding="utf-8").splitlines()
        if not urls:
            print("  ! no --urls-file provided — skipping jsonld", file=sys.stderr)
        else:
            print(f"→ JSON-LD: scraping {len(urls)} event pages")
            ds.merge(jsonld.collect(client, urls=urls))

    return ds


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="ethioscrape", description=__doc__)
    p.add_argument("--sources", default="musicbrainz,setlistfm",
                   help="Comma list: musicbrainz,setlistfm,jsonld")
    p.add_argument("--area", default="Ethiopia", help="MusicBrainz area filter")
    p.add_argument("--query", action="append", default=[],
                   help="Extra MusicBrainz query, e.g. 'tag:gospel' (repeatable)")
    p.add_argument("--limit", type=int, default=50, help="Max artists to discover")
    p.add_argument("--max-pages", type=int, default=2, help="setlist.fm pages per artist")
    p.add_argument("--urls-file", help="File of URLs (one per line) for the jsonld source")
    p.add_argument("--contact", help="Contact email added to the User-Agent (courtesy)")
    p.add_argument("--min-interval", type=float, default=1.0, help="Seconds between requests/host")
    p.add_argument("--ignore-robots", action="store_true", help="(Not recommended) skip robots.txt")
    p.add_argument("--out", default="out/dataset.json", help="Where to write the JSON dump")
    p.add_argument("--no-json", action="store_true", help="Do not write the JSON dump")
    p.add_argument("--database-url", help="Postgres URL to load into (canonical schema)")
    p.add_argument("--sample", action="store_true", help="Use built-in fixtures (offline)")
    p.add_argument("--check-setlistfm", action="store_true",
                   help="Validate SETLISTFM_API_KEY against the API and exit")
    p.add_argument("--setlistfm-daily-budget", type=int, default=1440,
                   help="Max setlist.fm requests per day (their cap is 1440)")
    p.add_argument("--budget-file", default="out/setlistfm_usage.json",
                   help="Where the daily setlist.fm usage counter is persisted")
    return p


def _check_setlistfm(args) -> int:
    from .sources import setlistfm

    api_key = os.environ.get("SETLISTFM_API_KEY")
    if not api_key:
        print("SETLISTFM_API_KEY is not set. Export it and try again.", file=sys.stderr)
        return 2
    client = PoliteClient(contact=args.contact, min_interval=args.min_interval)
    result = setlistfm.check_api_key(client, api_key)
    if result["ok"]:
        print(f"✓ setlist.fm key works. 'Mulatu Astatke' search: {result['total']} match(es).")
        if result["sample"]:
            print("  sample:", ", ".join(result["sample"]))
        return 0
    print(f"✗ setlist.fm key check failed: {result['error']}", file=sys.stderr)
    return 1


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)

    if args.check_setlistfm:
        return _check_setlistfm(args)

    if args.sample:
        from .fixtures import build_sample_dataset

        print("→ Using built-in sample fixtures (offline)")
        dataset = build_sample_dataset()
    else:
        dataset = _run_sources(args)

    print("\nCollected:", json.dumps(dataset.summary()))

    if not args.no_json:
        out_path = pathlib.Path(args.out)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(
            json.dumps(dataset.to_dict(), ensure_ascii=False, indent=2), encoding="utf-8"
        )
        print(f"Wrote {out_path}")

    if args.database_url:
        from .db import load

        print("Loading into database…")
        stats = load(dataset, args.database_url)
        print("Loaded:", json.dumps(stats))

    return 0


if __name__ == "__main__":
    raise SystemExit(main())

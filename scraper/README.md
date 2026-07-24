# EthioScrape

Collects **Ethiopian live-performance data** (secular, gospel, and other) from public
sources and normalises it into the **canonical Setlist Ethiopia schema**
(`artists`, `artist_names`, `venues`, `events`, `performances`, `setlist_items`).

Everything collected is marked `status='community'` with an evidence/source trail —
scraped rows are *suggestions for curators to verify*, never authoritative. This
matches the app's moderation model (see `docs/policies/anti-abuse-and-fabrication.md`).

## Sources

| Source | What it yields | Needs |
| --- | --- | --- |
| `musicbrainz` | Artists by area=Ethiopia (+ genre queries), aliases → native Amharic names for `artist_names` | nothing (open, CC0) |
| `setlistfm` | Real setlists → `events`, `performances`, `setlist_items` | free `SETLISTFM_API_KEY` |
| `jsonld` | Any event page embedding schema.org `MusicEvent` JSON-LD → `events`, `venues`, `performances` | a `--urls-file` |

Discovery uses MusicBrainz `area:Ethiopia`; add `--query 'tag:gospel'` (repeatable) to
target gospel or other religious music specifically.

## Setup

```bash
cd scraper
python3 -m venv .venv && . .venv/bin/activate
pip install -r requirements.txt
```

## Usage

```bash
# Offline demo — no network, no keys. Writes reviewable JSON.
python -m ethioscrape.main --sample --out out/sample.json

# Discover artists + setlists, write JSON for review.
SETLISTFM_API_KEY=xxx python -m ethioscrape.main \
    --sources musicbrainz,setlistfm --limit 50 --out out/data.json

# Scrape event pages that embed schema.org JSON-LD.
python -m ethioscrape.main --sources jsonld --urls-file urls.txt

# Load directly into Postgres/Supabase (canonical tables must already exist).
python -m ethioscrape.main --sample --database-url "$SUPABASE_DB_URL"

# Verify your setlist.fm key works before a real run.
SETLISTFM_API_KEY=xxx python -m ethioscrape.main --check-setlistfm
```

### setlist.fm rate limits

setlist.fm caps usage at **2 req/sec** and **1440 req/day**. The scraper stays inside
both automatically:

- 1 request/host/second by default (`--min-interval`), under the 2/sec ceiling.
- A **persistent daily budget**: it records how many setlist.fm requests it has made
  today (UTC) in `--budget-file` (default `out/setlistfm_usage.json`) and stops before
  exceeding `--setlistfm-daily-budget` (default `1440`) — even across multiple runs in
  the same day. Already-collected data is still written.

```bash
# Conservative run that will never exceed 500 setlist.fm calls today:
python -m ethioscrape.main --sources musicbrainz,setlistfm \
    --limit 200 --setlistfm-daily-budget 500
```

The default output is a JSON dump so you can **review before loading**. Add
`--database-url` to upsert into Postgres (idempotent: artists/venues/events upsert by
slug; performances are de-duplicated).

## Loading into Supabase

1. Ensure the canonical tables exist (they do in your deployed DB; a reference copy is
   `docs/database/canonical_supabase_schema.sql`).
2. Run with `--database-url` set to the Supabase **session/direct** connection string.
   Rows land as `status='community'` for curators to verify and promote.

## Responsible scraping

- Sends a descriptive `User-Agent` (add `--contact you@example.com`).
- Obeys `robots.txt` (override only with `--ignore-robots`, not recommended).
- Rate-limits to 1 request/host/second by default (`--min-interval`).
- Prefer the API sources (MusicBrainz, setlist.fm) over raw HTML where possible.

## Tests

```bash
pip install pytest
pytest                        # offline: parsers, dedupe, JSON round-trip
# Optional loader test against a throwaway Postgres — see tests/test_loader.py
```

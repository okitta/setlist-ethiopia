"""EthioScrape — collect Ethiopian live-performance data from public sources and
normalise it into the Setlist Ethiopia canonical schema.

Sources are pluggable (see `sources/`). Everything collected is marked
`status='community'` with a `source_url`/`evidence` trail, matching the app's
moderation model: scraped data is a *suggestion* for curators to verify, never
authoritative.
"""

__version__ = "0.1.0"

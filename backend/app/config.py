"""Application settings and feature flags.

Every risky or unfinished capability is placed behind a feature flag so it can be
enabled gradually and disabled instantly without a redeploy (see the release flow
in docs/governance/environments-and-release-flow.md).
"""

import os
from functools import lru_cache
from typing import Literal

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


def normalise_database_url(url: str) -> str:
    """Accept the URLs Supabase/Vercel hand out and return one SQLAlchemy can use.

    Supabase exposes `postgresql://` (or `postgres://`) connection strings; we pin the
    modern psycopg (v3) driver, so the scheme is rewritten to `postgresql+psycopg://`.
    SQLite URLs are returned unchanged.
    """
    if url.startswith("postgres://"):
        url = "postgresql+psycopg://" + url[len("postgres://") :]
    elif url.startswith("postgresql://"):
        url = "postgresql+psycopg://" + url[len("postgresql://") :]
    return url


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="SETLIST_",
        env_file=".env",
        extra="ignore",
    )

    environment: Literal["local", "preview", "staging", "production"] = "local"

    # SQLite by default for local/preview. In deployed environments the connection
    # string comes from SETLIST_DATABASE_URL, or from the platform-provided
    # DATABASE_URL / POSTGRES_URL (Vercel + Supabase) — see the validator below.
    database_url: str = "sqlite:///./setlist.db"

    # Structured-logging verbosity. Never log secrets or unnecessary personal data.
    log_level: str = "INFO"

    # --- Feature flags -----------------------------------------------------
    # Marking attendance collects a (user, performance) edge. Off by default in
    # brand-new environments until abuse controls are confirmed.
    feature_attendance: bool = True
    # Adding a single missing song to a setlist.
    feature_add_song: bool = True
    # The public, read-only data-reuse API (see docs/policies/data-reuse-and-api.md).
    feature_public_api: bool = True

    # Guard-rails used by the anti-fabrication rules (see app/moderation.py).
    # The earliest plausible performance date we will accept a record for.
    earliest_performance_year: int = 1930

    # Open-data licence advertised by the public API.
    data_license: str = "CC-BY-SA-4.0"
    data_license_url: str = "https://creativecommons.org/licenses/by-sa/4.0/"

    @model_validator(mode="after")
    def _resolve_database_url(self) -> "Settings":
        # If no explicit SETLIST_DATABASE_URL was given, adopt the platform's
        # Postgres URL (Vercel/Supabase) when present.
        if self.database_url.startswith("sqlite"):
            platform_url = os.environ.get("DATABASE_URL") or os.environ.get("POSTGRES_URL")
            if platform_url:
                self.database_url = platform_url
        self.database_url = normalise_database_url(self.database_url)
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()

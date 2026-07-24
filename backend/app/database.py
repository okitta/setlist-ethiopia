"""Database engine and session management."""

from collections.abc import Iterator

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.config import get_settings

settings = get_settings()
is_sqlite = settings.database_url.startswith("sqlite")

if is_sqlite:
    # check_same_thread is only needed for SQLite.
    engine = create_engine(
        settings.database_url,
        connect_args={"check_same_thread": False},
        future=True,
    )
else:
    # Postgres/Supabase. In serverless (Vercel) each invocation is short-lived, so we
    # keep the pool tiny, verify connections before use, and recycle them. When using
    # Supabase's transaction pooler (pgbouncer), server-side prepared statements are
    # disabled via prepare_threshold=None.
    engine = create_engine(
        settings.database_url,
        pool_size=1,
        max_overflow=2,
        pool_pre_ping=True,
        pool_recycle=300,
        connect_args={"prepare_threshold": None},
        future=True,
    )

SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


def get_db() -> Iterator[Session]:
    """FastAPI dependency yielding a request-scoped session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

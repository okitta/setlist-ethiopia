"""Public, read-only data-reuse API.

Answers the policy question 'whether contributed structured data can be reused
through an API': **yes** — non-personal, structured contribution data is openly
reusable under the licence in docs/policies/data-reuse-and-api.md.

Guarantees enforced here:

* **Read-only** — no write verbs are exposed.
* **No personal data** — no user handles, no per-user attendance; attendance is
  returned only as an aggregate count.
* **Only public, non-archived records** — archived (e.g. fabricated) records are
  excluded.
* **Self-describing licence** — every payload carries licence + attribution terms.

The whole surface is behind the `feature_public_api` flag so it can be disabled
instantly if abused.
"""

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import get_settings
from app.crud import attendance_count
from app.database import get_db
from app.models import Artist, Performance, SetlistEntry

router = APIRouter(prefix="/api/v1/public", tags=["public-data"])
settings = get_settings()


def _guard() -> None:
    if not settings.feature_public_api:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "feature_off", "message": "The public API is disabled."},
        )


def _license_block() -> dict:
    return {
        "license": settings.data_license,
        "license_url": settings.data_license_url,
        "attribution": "Setlist Ethiopia contributors",
        "terms": "Reuse permitted with attribution and share-alike. Excludes personal data.",
    }


@router.get("/license")
def license_info() -> dict:
    """Machine-readable statement of how this data may be reused."""
    return _license_block()


@router.get("/artists")
def public_artists(
    q: str | None = Query(default=None),
    limit: int = Query(default=100, le=500),
    db: Session = Depends(get_db),
) -> dict:
    _guard()
    stmt = select(Artist).where(Artist.is_archived.is_(False)).order_by(Artist.name)
    if q:
        stmt = stmt.where(Artist.name.ilike(f"%{q}%"))
    artists = db.scalars(stmt.limit(limit)).all()
    return {
        "meta": _license_block(),
        "data": [{"id": a.id, "name": a.name, "slug": a.slug, "bio": a.bio} for a in artists],
    }


@router.get("/performances/{performance_id}")
def public_performance(performance_id: int, db: Session = Depends(get_db)) -> dict:
    _guard()
    perf = db.get(Performance, performance_id)
    if perf is None or perf.is_archived:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "not_found", "message": "Performance not found."},
        )
    entries = db.scalars(
        select(SetlistEntry)
        .where(
            SetlistEntry.performance_id == perf.id,
            SetlistEntry.is_archived.is_(False),
        )
        .order_by(SetlistEntry.position)
    ).all()
    return {
        "meta": _license_block(),
        "data": {
            "id": perf.id,
            "artist_id": perf.artist_id,
            "venue": perf.venue,
            "city": perf.city,
            "performed_on": perf.performed_on.isoformat(),
            "notes": perf.notes,
            # Aggregate only — never who attended.
            "attendance_count": attendance_count(db, perf.id),
            "setlist": [{"position": e.position, "song": e.song.title} for e in entries],
        },
    }

"""Artist discovery — the entry point of the vertical slice ('find an artist')."""

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.crud import attendance_count
from app.database import get_db
from app.models import Artist, Performance
from app.schemas import ArtistOut, PerformanceOut

router = APIRouter(prefix="/api/v1/artists", tags=["artists"])


@router.get("", response_model=list[ArtistOut])
def search_artists(
    q: str | None = Query(default=None, description="Case-insensitive name search."),
    db: Session = Depends(get_db),
) -> list[Artist]:
    stmt = select(Artist).where(Artist.is_archived.is_(False)).order_by(Artist.name)
    if q:
        stmt = stmt.where(Artist.name.ilike(f"%{q}%"))
    return list(db.scalars(stmt.limit(50)))


@router.get("/{artist_id}/performances", response_model=list[PerformanceOut])
def list_performances(artist_id: int, db: Session = Depends(get_db)) -> list[PerformanceOut]:
    stmt = (
        select(Performance)
        .where(
            Performance.artist_id == artist_id,
            Performance.is_archived.is_(False),
        )
        .order_by(Performance.performed_on.desc())
    )
    performances = db.scalars(stmt).all()
    return [
        PerformanceOut(
            **PerformanceOut.model_validate(p).model_dump(exclude={"attendance_count"}),
            attendance_count=attendance_count(db, p.id),
        )
        for p in performances
    ]

"""Open a performance, create one, view its full revision history."""

from datetime import date

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.config import get_settings
from app.crud import attendance_count, record_revision
from app.database import get_db
from app.dependencies import get_current_user, require_curator
from app.logging_config import get_logger
from app.models import (
    Artist,
    Performance,
    Revision,
    RevisionAction,
    SetlistEntry,
    User,
    utcnow,
)
from app.moderation import (
    ModerationError,
    PerformanceFacts,
    check_performance_plausibility,
    screen_text,
)
from app.schemas import (
    PerformanceCreate,
    PerformanceDetail,
    RevisionOut,
    SetlistEntryOut,
)

router = APIRouter(prefix="/api/v1/performances", tags=["performances"])
logger = get_logger("performances")
settings = get_settings()


def _detail(db: Session, perf: Performance) -> PerformanceDetail:
    entries = db.scalars(
        select(SetlistEntry)
        .where(
            SetlistEntry.performance_id == perf.id,
            SetlistEntry.is_archived.is_(False),
        )
        .order_by(SetlistEntry.position)
    ).all()
    return PerformanceDetail(
        id=perf.id,
        artist_id=perf.artist_id,
        venue=perf.venue,
        city=perf.city,
        performed_on=perf.performed_on,
        notes=perf.notes,
        is_archived=perf.is_archived,
        attendance_count=attendance_count(db, perf.id),
        setlist=[
            SetlistEntryOut(
                id=e.id,
                position=e.position,
                song_id=e.song_id,
                song_title=e.song.title,
                is_archived=e.is_archived,
            )
            for e in entries
        ],
    )


def _get_active_performance(db: Session, performance_id: int) -> Performance:
    perf = db.get(Performance, performance_id)
    if perf is None or perf.is_archived:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "not_found", "message": "Performance not found."},
        )
    return perf


@router.get("/{performance_id}", response_model=PerformanceDetail)
def open_performance(performance_id: int, db: Session = Depends(get_db)) -> PerformanceDetail:
    return _detail(db, _get_active_performance(db, performance_id))


@router.post("", response_model=PerformanceDetail, status_code=status.HTTP_201_CREATED)
def create_performance(
    body: PerformanceCreate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> PerformanceDetail:
    if db.get(Artist, body.artist_id) is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "not_found", "message": "Artist not found."},
        )

    # Anti-abuse gate: screen notes for harassment and validate the record is not
    # physically impossible / fabricated.
    try:
        screen_text(body.notes, field="notes")
        check_performance_plausibility(
            PerformanceFacts(body.performed_on, body.venue, body.city),
            today=date.today(),
            earliest_year=settings.earliest_performance_year,
        )
    except ModerationError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={"code": exc.code, "message": exc.message},
        ) from exc

    perf = Performance(
        artist_id=body.artist_id,
        venue=body.venue.strip(),
        city=body.city.strip(),
        performed_on=body.performed_on,
        notes=body.notes,
        created_by=user.id,
    )
    db.add(perf)
    try:
        db.flush()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "code": "duplicate_performance",
                "message": "This artist already has a record for that venue and date.",
            },
        ) from exc

    record_revision(
        db,
        entity_type="performance",
        entity_id=perf.id,
        action=RevisionAction.create,
        summary=f"Documented show at {perf.venue}, {perf.city}",
        actor_id=user.id,
    )
    db.commit()
    db.refresh(perf)
    logger.info(
        "performance_created",
        extra={"context": {"performance_id": perf.id, "actor_id": user.id}},
    )
    return _detail(db, perf)


@router.post("/{performance_id}/archive", response_model=PerformanceDetail)
def archive_performance(
    performance_id: int,
    db: Session = Depends(get_db),
    curator: User = Depends(require_curator),
) -> PerformanceDetail:
    """Soft-delete a performance (e.g. confirmed fabricated). History is preserved."""
    perf = _get_active_performance(db, performance_id)
    perf.is_archived = True
    perf.archived_at = utcnow()
    record_revision(
        db,
        entity_type="performance",
        entity_id=perf.id,
        action=RevisionAction.archive,
        summary="Archived by curator",
        actor_id=curator.id,
    )
    db.commit()
    db.refresh(perf)
    return _detail(db, perf)


@router.get("/{performance_id}/revisions", response_model=list[RevisionOut])
def performance_revisions(performance_id: int, db: Session = Depends(get_db)) -> list[Revision]:
    """The contribution & revision history for a performance and its setlist."""
    entry_ids = [
        e.id
        for e in db.scalars(
            select(SetlistEntry).where(SetlistEntry.performance_id == performance_id)
        )
    ]
    stmt = (
        select(Revision)
        .where(
            ((Revision.entity_type == "performance") & (Revision.entity_id == performance_id))
            | (
                (Revision.entity_type == "setlist_entry")
                & (Revision.entity_id.in_(entry_ids or [-1]))
            )
        )
        .order_by(Revision.created_at.desc())
    )
    return list(db.scalars(stmt))

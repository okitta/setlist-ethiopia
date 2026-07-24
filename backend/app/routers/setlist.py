"""Add one missing song to a performance's setlist (feature-flagged)."""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.config import get_settings
from app.crud import get_or_create_song, record_revision
from app.database import get_db
from app.dependencies import get_current_user
from app.logging_config import get_logger
from app.models import Performance, RevisionAction, SetlistEntry, User
from app.moderation import ModerationError, screen_text
from app.schemas import AddSongRequest, SetlistEntryOut

router = APIRouter(prefix="/api/v1/performances", tags=["setlist"])
logger = get_logger("setlist")
settings = get_settings()


@router.post(
    "/{performance_id}/songs",
    response_model=SetlistEntryOut,
    status_code=status.HTTP_201_CREATED,
)
def add_song(
    performance_id: int,
    body: AddSongRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> SetlistEntryOut:
    if not settings.feature_add_song:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "feature_off", "message": "Adding songs is not available."},
        )

    perf = db.get(Performance, performance_id)
    if perf is None or perf.is_archived:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "not_found", "message": "Performance not found."},
        )

    try:
        screen_text(body.title, field="song title")
    except ModerationError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={"code": exc.code, "message": exc.message},
        ) from exc

    song = get_or_create_song(db, body.title)

    # Prevent the same song being listed twice in one setlist (a common fabrication
    # / duplication error).
    already = db.scalar(
        select(SetlistEntry).where(
            SetlistEntry.performance_id == performance_id,
            SetlistEntry.song_id == song.id,
            SetlistEntry.is_archived.is_(False),
        )
    )
    if already is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "code": "duplicate_song",
                "message": "That song is already in this setlist.",
            },
        )

    if body.position is None:
        max_pos = db.scalar(
            select(func.max(SetlistEntry.position)).where(
                SetlistEntry.performance_id == performance_id
            )
        )
        position = (max_pos or 0) + 1
    else:
        position = body.position

    entry = SetlistEntry(
        performance_id=performance_id,
        song_id=song.id,
        position=position,
        created_by=user.id,
    )
    db.add(entry)
    try:
        db.flush()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "code": "position_taken",
                "message": f"Position {position} is already used in this setlist.",
            },
        ) from exc

    record_revision(
        db,
        entity_type="setlist_entry",
        entity_id=entry.id,
        action=RevisionAction.create,
        summary=f"Added '{song.title}' at position {position}",
        actor_id=user.id,
    )
    db.commit()
    db.refresh(entry)
    logger.info(
        "song_added",
        extra={"context": {"performance_id": performance_id, "actor_id": user.id}},
    )
    return SetlistEntryOut(
        id=entry.id,
        position=entry.position,
        song_id=song.id,
        song_title=song.title,
        is_archived=entry.is_archived,
    )

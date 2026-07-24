"""Data-access helpers shared across routers.

Notable responsibility: every mutation goes through `record_revision`, which appends
to the immutable history so contributions are always attributable and reversible.
"""

import re

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import (
    Attendance,
    Revision,
    RevisionAction,
    Song,
)


def slugify(value: str) -> str:
    value = re.sub(r"[^\w\s-]", "", value, flags=re.UNICODE).strip().casefold()
    slug = re.sub(r"[\s_-]+", "-", value)
    return slug or "item"


def record_revision(
    db: Session,
    *,
    entity_type: str,
    entity_id: int,
    action: RevisionAction,
    summary: str,
    actor_id: int | None,
) -> Revision:
    """Append an immutable history entry. Callers must still commit the session."""
    rev = Revision(
        entity_type=entity_type,
        entity_id=entity_id,
        action=action,
        summary=summary,
        actor_id=actor_id,
    )
    db.add(rev)
    return rev


def attendance_count(db: Session, performance_id: int) -> int:
    return (
        db.scalar(
            select(func.count(Attendance.id)).where(
                Attendance.performance_id == performance_id,
                Attendance.is_archived.is_(False),
            )
        )
        or 0
    )


def get_or_create_song(db: Session, title: str) -> Song:
    slug = slugify(title)
    song = db.scalar(select(Song).where(Song.slug == slug))
    if song is None:
        song = Song(title=title.strip(), slug=slug)
        db.add(song)
        db.flush()
    return song

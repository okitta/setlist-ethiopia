"""Mark / unmark attendance at a performance (feature-flagged)."""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import get_settings
from app.crud import attendance_count
from app.database import get_db
from app.dependencies import get_current_user
from app.logging_config import get_logger
from app.models import Attendance, Performance, User
from app.schemas import AttendanceOut

router = APIRouter(prefix="/api/v1/performances", tags=["attendance"])
logger = get_logger("attendance")
settings = get_settings()


def _guard(db: Session, performance_id: int) -> Performance:
    if not settings.feature_attendance:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "feature_off", "message": "Attendance is not available."},
        )
    perf = db.get(Performance, performance_id)
    if perf is None or perf.is_archived:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "not_found", "message": "Performance not found."},
        )
    return perf


@router.post("/{performance_id}/attendance", response_model=AttendanceOut)
def mark_attendance(
    performance_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> AttendanceOut:
    _guard(db, performance_id)
    existing = db.scalar(
        select(Attendance).where(
            Attendance.performance_id == performance_id,
            Attendance.user_id == user.id,
        )
    )
    if existing is None:
        db.add(Attendance(performance_id=performance_id, user_id=user.id))
    elif existing.is_archived:
        existing.is_archived = False
    db.commit()
    logger.info(
        "attendance_marked",
        extra={"context": {"performance_id": performance_id, "actor_id": user.id}},
    )
    return AttendanceOut(
        performance_id=performance_id,
        attending=True,
        attendance_count=attendance_count(db, performance_id),
    )


@router.delete("/{performance_id}/attendance", response_model=AttendanceOut)
def unmark_attendance(
    performance_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> AttendanceOut:
    _guard(db, performance_id)
    existing = db.scalar(
        select(Attendance).where(
            Attendance.performance_id == performance_id,
            Attendance.user_id == user.id,
        )
    )
    if existing is not None and not existing.is_archived:
        existing.is_archived = True  # soft-remove; keeps the historical edge
        db.commit()
    return AttendanceOut(
        performance_id=performance_id,
        attending=False,
        attendance_count=attendance_count(db, performance_id),
    )

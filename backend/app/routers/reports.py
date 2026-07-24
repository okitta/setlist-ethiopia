"""Community abuse reports and curator resolution.

This is the human side of the anti-abuse policy: anything the automated rules in
app/moderation.py cannot decide (subtle fabrication, context-dependent harassment)
is surfaced here for curators, without silently altering the reported record.
"""

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_current_user, require_curator
from app.logging_config import get_logger
from app.models import Report, ReportStatus, User, utcnow
from app.schemas import ReportCreate, ReportOut

router = APIRouter(prefix="/api/v1/reports", tags=["moderation"])
logger = get_logger("reports")


@router.post("", response_model=ReportOut, status_code=status.HTTP_201_CREATED)
def create_report(
    body: ReportCreate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> Report:
    report = Report(
        entity_type=body.entity_type,
        entity_id=body.entity_id,
        reason=body.reason,
        details=body.details,
        reporter_id=user.id,
    )
    db.add(report)
    db.commit()
    db.refresh(report)
    # Log identifiers only — never the free-text details (may contain personal data).
    logger.info(
        "report_filed",
        extra={
            "context": {
                "report_id": report.id,
                "entity_type": report.entity_type,
                "reason": report.reason,
            }
        },
    )
    return report


@router.get("", response_model=list[ReportOut])
def list_reports(
    status_filter: str | None = Query(default="open", alias="status"),
    db: Session = Depends(get_db),
    curator: User = Depends(require_curator),
) -> list[Report]:
    stmt = select(Report).order_by(Report.created_at.desc())
    if status_filter:
        stmt = stmt.where(Report.status == status_filter)
    return list(db.scalars(stmt))


@router.post("/{report_id}/resolve", response_model=ReportOut)
def resolve_report(
    report_id: int,
    upheld: bool = Query(description="True if the report is valid and action taken."),
    db: Session = Depends(get_db),
    curator: User = Depends(require_curator),
) -> Report:
    report = db.get(Report, report_id)
    if report is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "not_found", "message": "Report not found."},
        )
    report.status = ReportStatus.upheld if upheld else ReportStatus.dismissed
    report.resolver_id = curator.id
    report.resolved_at = utcnow()
    db.commit()
    db.refresh(report)
    return report

"""SQLAlchemy models for the community performance archive.

Design principles baked into the schema (see docs/governance/sdlc-principles.md):

* **Never delete contribution history silently.** Records are archived, not deleted
  (`archived_at` / `is_archived`), and every mutation writes an immutable `Revision`.
* **Attribution everywhere.** Contributions carry the acting user so fabricated or
  abusive records are traceable and reversible.
"""

from datetime import UTC, date, datetime
from enum import Enum

from sqlalchemy import (
    Date,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


def utcnow() -> datetime:
    return datetime.now(UTC)


class Role(str, Enum):
    contributor = "contributor"
    curator = "curator"
    admin = "admin"


class ReportStatus(str, Enum):
    open = "open"
    reviewing = "reviewing"
    upheld = "upheld"
    dismissed = "dismissed"


class RevisionAction(str, Enum):
    create = "create"
    update = "update"
    archive = "archive"
    restore = "restore"


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    handle: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    display_name: Mapped[str] = mapped_column(String(120))
    role: Mapped[Role] = mapped_column(String(20), default=Role.contributor)
    is_active: Mapped[bool] = mapped_column(default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class Artist(Base):
    __tablename__ = "artists"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(200), index=True)
    slug: Mapped[str] = mapped_column(String(220), unique=True, index=True)
    bio: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_archived: Mapped[bool] = mapped_column(default=False, index=True)
    archived_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_by: Mapped[int | None] = mapped_column(ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    performances: Mapped[list["Performance"]] = relationship(back_populates="artist")


class Performance(Base):
    __tablename__ = "performances"
    __table_args__ = (
        # Anti-fabrication: the same artist cannot have two live records for the
        # same venue on the same day.
        UniqueConstraint("artist_id", "venue", "performed_on", name="uq_perf_artist_venue_date"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    artist_id: Mapped[int] = mapped_column(ForeignKey("artists.id"), index=True)
    venue: Mapped[str] = mapped_column(String(200))
    city: Mapped[str] = mapped_column(String(120))
    performed_on: Mapped[date] = mapped_column(Date, index=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_archived: Mapped[bool] = mapped_column(default=False, index=True)
    archived_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_by: Mapped[int | None] = mapped_column(ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    artist: Mapped[Artist] = relationship(back_populates="performances")
    setlist: Mapped[list["SetlistEntry"]] = relationship(back_populates="performance")


class Song(Base):
    __tablename__ = "songs"

    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(String(240), index=True)
    slug: Mapped[str] = mapped_column(String(260), unique=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class SetlistEntry(Base):
    __tablename__ = "setlist_entries"
    __table_args__ = (
        UniqueConstraint("performance_id", "position", name="uq_setlist_perf_position"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    performance_id: Mapped[int] = mapped_column(ForeignKey("performances.id"), index=True)
    song_id: Mapped[int] = mapped_column(ForeignKey("songs.id"))
    position: Mapped[int] = mapped_column(Integer)
    is_archived: Mapped[bool] = mapped_column(default=False, index=True)
    archived_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_by: Mapped[int | None] = mapped_column(ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    performance: Mapped[Performance] = relationship(back_populates="setlist")
    song: Mapped[Song] = relationship()


class Attendance(Base):
    __tablename__ = "attendances"
    __table_args__ = (UniqueConstraint("performance_id", "user_id", name="uq_attendance_once"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    performance_id: Mapped[int] = mapped_column(ForeignKey("performances.id"), index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    is_archived: Mapped[bool] = mapped_column(default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class Revision(Base):
    """Immutable contribution & revision history. Append-only; never updated or
    deleted. This is what powers 'see the contribution and revision history'."""

    __tablename__ = "revisions"

    id: Mapped[int] = mapped_column(primary_key=True)
    entity_type: Mapped[str] = mapped_column(String(40), index=True)
    entity_id: Mapped[int] = mapped_column(Integer, index=True)
    action: Mapped[RevisionAction] = mapped_column(String(20))
    summary: Mapped[str] = mapped_column(String(280))
    actor_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, index=True
    )


class Report(Base):
    """Community abuse reports (harassment, fabricated records, etc.)."""

    __tablename__ = "reports"

    id: Mapped[int] = mapped_column(primary_key=True)
    entity_type: Mapped[str] = mapped_column(String(40), index=True)
    entity_id: Mapped[int] = mapped_column(Integer, index=True)
    reason: Mapped[str] = mapped_column(String(40))
    details: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[ReportStatus] = mapped_column(String(20), default=ReportStatus.open, index=True)
    reporter_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"))
    resolver_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

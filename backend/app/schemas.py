"""Pydantic request/response models (the API contract)."""

from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field


class ORMModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


# --- Artists ---------------------------------------------------------------
class ArtistOut(ORMModel):
    id: int
    name: str
    slug: str
    bio: str | None = None
    is_archived: bool


# --- Performances ----------------------------------------------------------
class PerformanceCreate(BaseModel):
    artist_id: int
    venue: str = Field(min_length=1, max_length=200)
    city: str = Field(min_length=1, max_length=120)
    performed_on: date
    notes: str | None = Field(default=None, max_length=4000)


class SetlistEntryOut(ORMModel):
    id: int
    position: int
    song_id: int
    song_title: str
    is_archived: bool


class PerformanceOut(ORMModel):
    id: int
    artist_id: int
    venue: str
    city: str
    performed_on: date
    notes: str | None = None
    is_archived: bool
    attendance_count: int = 0


class PerformanceDetail(PerformanceOut):
    setlist: list[SetlistEntryOut] = []


# --- Setlist ---------------------------------------------------------------
class AddSongRequest(BaseModel):
    """Add one missing song to a performance's setlist."""

    title: str = Field(min_length=1, max_length=240)
    position: int | None = Field(
        default=None, ge=1, description="1-based slot; appended to the end if omitted."
    )


# --- Attendance ------------------------------------------------------------
class AttendanceOut(BaseModel):
    performance_id: int
    attending: bool
    attendance_count: int


# --- Reports ---------------------------------------------------------------
class ReportCreate(BaseModel):
    entity_type: str = Field(pattern="^(artist|performance|setlist_entry)$")
    entity_id: int
    reason: str = Field(pattern="^(harassment|fabricated|spam|other)$")
    details: str | None = Field(default=None, max_length=2000)


class ReportOut(ORMModel):
    id: int
    entity_type: str
    entity_id: int
    reason: str
    status: str
    created_at: datetime


# --- Revisions -------------------------------------------------------------
class RevisionOut(ORMModel):
    id: int
    entity_type: str
    entity_id: int
    action: str
    summary: str
    actor_id: int | None = None
    created_at: datetime


# --- Errors ----------------------------------------------------------------
class ErrorOut(BaseModel):
    code: str
    message: str

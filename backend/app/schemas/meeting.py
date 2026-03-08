from datetime import datetime

from pydantic import BaseModel, Field

from app.models.meeting import TranscriptStatus
from app.schemas.base import PyObjectId


class MeetingCreate(BaseModel):
    project_id: str
    title: str = Field(min_length=1, max_length=255)
    meeting_date: datetime | None = None


class MeetingUpdate(BaseModel):
    title: str | None = Field(default=None, max_length=255)
    meeting_date: datetime | None = None


class MeetingResponse(BaseModel):
    model_config = {"from_attributes": True}

    id: PyObjectId
    project_id: PyObjectId
    team_id: PyObjectId
    title: str
    meeting_date: datetime | None
    created_by: PyObjectId
    created_at: datetime


class TranscriptStatusResponse(BaseModel):
    model_config = {"from_attributes": True}

    id: PyObjectId
    meeting_id: PyObjectId
    processing_status: TranscriptStatus
    error_message: str | None
    created_at: datetime
    processed_at: datetime | None


class MeetingSummaryResponse(BaseModel):
    model_config = {"from_attributes": True}

    summary_text: str | None
    key_points: list | None
    decisions: list | None
    created_at: datetime

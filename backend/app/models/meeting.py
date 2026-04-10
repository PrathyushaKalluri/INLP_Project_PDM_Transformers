import enum
from datetime import datetime, timezone

from beanie import Document, PydanticObjectId
from pydantic import BaseModel, Field
from pymongo import ASCENDING, IndexModel


class TranscriptStatus(str, enum.Enum):
    PENDING = "PENDING"
    PROCESSING = "PROCESSING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


class MeetingSummary(BaseModel):
    """Embedded inside a Meeting document — not a separate collection."""

    summary_text: str | None = None
    key_points: list | None = None
    decisions: list | None = None
    raw_nlp_output: dict | None = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class Meeting(Document):
    project_id: PydanticObjectId
    team_id: PydanticObjectId
    title: str
    meeting_date: datetime | None = None
    created_by: PydanticObjectId
    summary: MeetingSummary | None = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    class Settings:
        name = "meetings"
        indexes = [
            IndexModel([("project_id", ASCENDING)]),
            IndexModel([("team_id", ASCENDING)]),
            IndexModel([("meeting_date", ASCENDING)]),
        ]


class Transcript(Document):
    meeting_id: PydanticObjectId
    file_path: str | None = None
    raw_text: str
    processing_status: TranscriptStatus = TranscriptStatus.PENDING
    error_message: str | None = None
    uploaded_by: PydanticObjectId
    processed_at: datetime | None = None
    
    # Phase X: Result Persistence — Store NLP output
    summary_text: str | None = None
    action_items: list[dict] = []  # [{"title": str, "description": str, "assignee": str|None, "deadline": str|None}]
    action_item_ids: list[PydanticObjectId] = []  # Task IDs created from this transcript (Phase IV: Publish completion)
    
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    class Settings:
        name = "transcripts"
        indexes = [IndexModel([("meeting_id", ASCENDING)], unique=True)]

import enum
from datetime import date, datetime, timezone

from beanie import Document, PydanticObjectId
from bson import ObjectId
from pydantic import BaseModel, Field
from pymongo import ASCENDING, IndexModel


class TaskStatus(str, enum.Enum):
    BACKLOG = "BACKLOG"
    TODO = "TODO"
    IN_PROGRESS = "IN_PROGRESS"
    IN_REVIEW = "IN_REVIEW"
    DONE = "DONE"
    CANCELLED = "CANCELLED"


class TaskPriority(str, enum.Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class SuggestionReviewStatus(str, enum.Enum):
    PENDING = "PENDING"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    MODIFIED = "MODIFIED"


# ─── Embedded sub-documents ──────────────────────────────────────────────────

class SubTask(BaseModel):
    id: PydanticObjectId = Field(default_factory=ObjectId)
    title: str
    description: str | None = None
    status: str = "TODO"
    assignee_id: PydanticObjectId | None = None
    created_by: PydanticObjectId
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class TaskNote(BaseModel):
    id: PydanticObjectId = Field(default_factory=ObjectId)
    content: str
    created_by: PydanticObjectId
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class TaskEvidence(BaseModel):
    id: PydanticObjectId = Field(default_factory=ObjectId)
    transcript_id: PydanticObjectId
    speaker: str | None = None
    transcript_timestamp: str | None = None
    quote: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class TaskStatusHistory(BaseModel):
    id: PydanticObjectId = Field(default_factory=ObjectId)
    old_status: str | None = None
    new_status: str
    changed_by: PydanticObjectId
    changed_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


# ─── Collections ─────────────────────────────────────────────────────────────

class TaskSuggestion(Document):
    """NLP-extracted action items awaiting Project Owner review."""

    meeting_id: PydanticObjectId
    transcript_id: PydanticObjectId
    suggested_title: str
    suggested_description: str | None = None
    suggested_assignee_name: str | None = None
    suggested_deadline: date | None = None
    speaker: str | None = None
    transcript_quote: str | None = None
    transcript_timestamp: str | None = None
    review_status: SuggestionReviewStatus = SuggestionReviewStatus.PENDING
    reviewed_by: PydanticObjectId | None = None
    task_id: PydanticObjectId | None = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    class Settings:
        name = "task_suggestions"
        indexes = [
            IndexModel([("meeting_id", ASCENDING)]),
            IndexModel([("review_status", ASCENDING)]),
        ]


class Task(Document):
    project_id: PydanticObjectId
    team_id: PydanticObjectId
    meeting_id: PydanticObjectId | None = None
    task_suggestion_id: PydanticObjectId | None = None
    transcript_reference: PydanticObjectId | None = None
    title: str
    description: str | None = None
    status: TaskStatus = TaskStatus.BACKLOG
    priority: TaskPriority = TaskPriority.MEDIUM
    assignee_id: PydanticObjectId | None = None
    owner_id: PydanticObjectId | None = None
    created_by: PydanticObjectId
    due_date: date | None = None
    is_manual: bool = False
    position: int = 0
    evidence: list[TaskEvidence] = []
    subtasks: list[SubTask] = []
    notes: list[TaskNote] = []
    status_history: list[TaskStatusHistory] = []
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    class Settings:
        name = "tasks"
        indexes = [
            IndexModel([("project_id", ASCENDING), ("status", ASCENDING)]),
            IndexModel([("team_id", ASCENDING)]),
            IndexModel([("assignee_id", ASCENDING)]),
            IndexModel([("meeting_id", ASCENDING)]),
            IndexModel([("transcript_reference", ASCENDING), ("is_manual", ASCENDING)]),
        ]

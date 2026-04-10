import enum
from datetime import datetime, timezone

from beanie import Document, PydanticObjectId
from pydantic import Field
from pymongo import ASCENDING, IndexModel


class JobStatus(str, enum.Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    FAILED = "failed"
    TIMEOUT = "timeout"


# Total pipeline steps for progress calculation
JOB_TOTAL_STEPS = 6


class Job(Document):
    transcript_id: PydanticObjectId
    project_id: PydanticObjectId
    requester_id: PydanticObjectId | None = None
    status: JobStatus = JobStatus.PENDING
    current_step: int = 0
    step_label: str = "Queued"
    summary: str | None = None
    action_item_ids: list[PydanticObjectId] = []
    error_message: str | None = None
    cancel_requested: bool = False
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    class Settings:
        name = "jobs"
        indexes = [
            IndexModel([("project_id", ASCENDING)]),
            IndexModel([("transcript_id", ASCENDING)]),
            IndexModel([("status", ASCENDING)]),
        ]

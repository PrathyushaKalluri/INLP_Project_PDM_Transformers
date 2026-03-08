from datetime import date, datetime

from pydantic import BaseModel, Field

from app.models.task import SuggestionReviewStatus, TaskPriority, TaskStatus
from app.schemas.base import PyObjectId    


# â”€â”€ Task Suggestion â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

class TaskSuggestionResponse(BaseModel):
    model_config = {"from_attributes": True}

    id: PyObjectId
    meeting_id: PyObjectId
    transcript_id: PyObjectId
    suggested_title: str
    suggested_description: str | None
    suggested_assignee_name: str | None
    suggested_deadline: date | None
    speaker: str | None
    transcript_quote: str | None
    transcript_timestamp: str | None
    review_status: SuggestionReviewStatus
    reviewed_by: PyObjectId | None
    task_id: PyObjectId | None
    created_at: datetime


class SuggestionReviewUpdate(BaseModel):
    """Fields a Project Owner can edit before approving a suggestion."""
    suggested_title: str | None = Field(default=None, max_length=500)
    suggested_description: str | None = None
    assignee_id: str | None = None
    owner_id: str | None = None
    suggested_deadline: date | None = None
    priority: TaskPriority = TaskPriority.MEDIUM


class SuggestionApproveRequest(BaseModel):
    """Approve a suggestion, optionally overriding fields before creating the task."""
    title: str | None = Field(default=None, max_length=500)
    description: str | None = None
    assignee_id: str | None = None
    owner_id: str | None = None
    due_date: date | None = None
    priority: TaskPriority = TaskPriority.MEDIUM
    status: TaskStatus = TaskStatus.BACKLOG


# â”€â”€ Task â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

class TaskCreate(BaseModel):
    project_id: str
    title: str = Field(min_length=1, max_length=500)
    description: str | None = None
    assignee_id: str | None = None
    owner_id: str | None = None
    due_date: date | None = None
    priority: TaskPriority = TaskPriority.MEDIUM
    status: TaskStatus = TaskStatus.BACKLOG


class TaskUpdate(BaseModel):
    title: str | None = Field(default=None, max_length=500)
    description: str | None = None
    assignee_id: str | None = None
    owner_id: str | None = None
    due_date: date | None = None
    priority: TaskPriority | None = None
    status: TaskStatus | None = None
    position: int | None = None


class TaskResponse(BaseModel):
    model_config = {"from_attributes": True}

    id: PyObjectId
    project_id: PyObjectId
    team_id: PyObjectId
    meeting_id: PyObjectId | None
    task_suggestion_id: PyObjectId | None
    title: str
    description: str | None
    status: TaskStatus
    priority: TaskPriority
    assignee_id: PyObjectId | None
    owner_id: PyObjectId | None
    created_by: PyObjectId
    due_date: date | None
    is_manual: bool
    position: int
    created_at: datetime
    updated_at: datetime


# â”€â”€ Task Evidence â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

class TaskEvidenceResponse(BaseModel):
    model_config = {"from_attributes": True}

    id: PyObjectId
    transcript_id: PyObjectId | None
    speaker: str | None
    transcript_timestamp: str | None
    quote: str
    created_at: datetime


# â”€â”€ SubTask â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

class SubTaskCreate(BaseModel):
    title: str = Field(min_length=1, max_length=500)
    description: str | None = None
    assignee_id: str | None = None


class SubTaskUpdate(BaseModel):
    title: str | None = Field(default=None, max_length=500)
    description: str | None = None
    status: str | None = None
    assignee_id: str | None = None


class SubTaskResponse(BaseModel):
    model_config = {"from_attributes": True}

    id: PyObjectId
    title: str
    description: str | None
    status: str
    assignee_id: PyObjectId | None
    created_by: PyObjectId
    created_at: datetime
    updated_at: datetime


# â”€â”€ Task Note â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

class TaskNoteCreate(BaseModel):
    content: str = Field(min_length=1)


class TaskNoteResponse(BaseModel):
    model_config = {"from_attributes": True}

    id: PyObjectId
    content: str
    created_by: PyObjectId
    created_at: datetime
    updated_at: datetime


# â”€â”€ Status History â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

class TaskStatusHistoryResponse(BaseModel):
    model_config = {"from_attributes": True}

    id: PyObjectId
    old_status: str | None
    new_status: str
    changed_by: PyObjectId
    changed_at: datetime


# â”€â”€ Pagination wrapper â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

class PaginatedResponse(BaseModel):
    total: int
    page: int
    limit: int
    items: list


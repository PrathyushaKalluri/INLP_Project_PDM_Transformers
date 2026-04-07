from app.models.user import User, Workspace, WorkspaceMember, Team, TeamMember, WorkspaceRole, TeamRole
from app.models.project import Project
from app.models.meeting import Meeting, Transcript, MeetingSummary, TranscriptStatus
from app.models.task import (
    Task,
    TaskSuggestion,
    TaskEvidence,
    SubTask,
    TaskNote,
    TaskStatusHistory,
    TaskStatus,
    TaskPriority,
    SuggestionReviewStatus,
)


def get_document_models() -> list:
    """Return all Beanie Document classes for init_beanie()."""
    return [User, Workspace, Team, Project, Meeting, Transcript, TaskSuggestion, Task]


__all__ = [
    "User",
    "Workspace",
    "WorkspaceMember",
    "Team",
    "TeamMember",
    "WorkspaceRole",
    "TeamRole",
    "Project",
    "Meeting",
    "Transcript",
    "MeetingSummary",
    "TranscriptStatus",
    "Task",
    "TaskSuggestion",
    "TaskEvidence",
    "SubTask",
    "TaskNote",
    "TaskStatusHistory",
    "TaskStatus",
    "TaskPriority",
    "SuggestionReviewStatus",
    "get_document_models",
]

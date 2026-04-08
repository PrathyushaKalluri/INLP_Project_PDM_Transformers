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
from app.models.processing import Job, JobStatus
from app.models.notification import Notification, NotificationType


def get_document_models() -> list:
    """Return all Beanie Document classes for init_beanie()."""
    return [
        User,
        Workspace,
        Team,
        Project,
        Meeting,
        Transcript,
        TaskSuggestion,
        Task,
        Job,
        Notification,
    ]


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
    "Job",
    "JobStatus",
    "Notification",
    "NotificationType",
    "get_document_models",
]

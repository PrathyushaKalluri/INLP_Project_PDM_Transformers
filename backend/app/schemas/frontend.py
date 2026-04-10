from datetime import date

from pydantic import BaseModel, Field


class AuthSignupRequest(BaseModel):
    email: str
    password: str
    full_name: str = Field(alias="fullName")


class LogoutRequest(BaseModel):
    refresh_token: str | None = Field(default=None, alias="refreshToken")


class FrontendProjectCreate(BaseModel):
    team_id: str = Field(alias="teamId")
    name: str
    description: str | None = None


class FrontendProjectUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    is_archived: bool | None = Field(default=None, alias="isArchived")


class FrontendAddParticipant(BaseModel):
    user_id: str = Field(alias="userId")


class FrontendTaskCreate(BaseModel):
    project_id: str = Field(alias="projectId")
    title: str
    description: str | None = None
    assignee_ids: list[str] = Field(default_factory=list, alias="assigneeIds")
    owner_id: str | None = Field(default=None, alias="ownerId")
    deadline: date | None = None


class FrontendTaskUpdate(BaseModel):
    title: str | None = None
    description: str | None = None
    assignee_ids: list[str] | None = Field(default=None, alias="assigneeIds")
    owner_id: str | None = Field(default=None, alias="ownerId")
    deadline: date | None = None
    status: str | None = None
    priority: str | None = None


class FrontendTranscriptCreate(BaseModel):
    project_id: str = Field(alias="projectId")
    transcript_text: str = Field(alias="transcriptText")
    meeting_id: str | None = Field(default=None, alias="meetingId")
    meeting_title: str = Field(default="Transcript Upload", alias="meetingTitle")


class FrontendStartProcessingRequest(BaseModel):
    transcript_id: str = Field(alias="transcriptId")
    project_id: str = Field(alias="projectId")


class FrontendPublishRequest(BaseModel):
    """
    Simple publish contract: frontend only needs to provide:
    - projectId: which project to publish to
    - transcriptId: which transcript to get action items from
    
    Backend fetches action items from transcript (already extracted during NLP processing)
    """
    project_id: str = Field(alias="projectId")
    transcript_id: str = Field(alias="transcriptId")


class NotificationsReadRequest(BaseModel):
    ids: list[str] | None = None

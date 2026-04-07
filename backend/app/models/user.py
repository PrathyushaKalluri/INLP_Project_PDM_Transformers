import enum
from datetime import datetime, timezone

from beanie import Document, PydanticObjectId
from pydantic import BaseModel, Field
from pymongo import ASCENDING, IndexModel


class WorkspaceRole(str, enum.Enum):
    ADMIN = "ADMIN"
    MEMBER = "MEMBER"


class TeamRole(str, enum.Enum):
    OWNER = "OWNER"
    MEMBER = "MEMBER"


class User(Document):
    email: str
    hashed_password: str
    full_name: str = ""
    is_active: bool = True
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    class Settings:
        name = "users"
        indexes = [IndexModel([("email", ASCENDING)], unique=True)]


class WorkspaceMember(BaseModel):
    user_id: PydanticObjectId
    role: WorkspaceRole = WorkspaceRole.MEMBER
    joined_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class Workspace(Document):
    name: str
    slug: str
    created_by: PydanticObjectId
    members: list[WorkspaceMember] = []
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    class Settings:
        name = "workspaces"
        indexes = [IndexModel([("slug", ASCENDING)], unique=True)]


class TeamMember(BaseModel):
    user_id: PydanticObjectId
    role: TeamRole = TeamRole.MEMBER
    joined_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class Team(Document):
    workspace_id: PydanticObjectId
    name: str
    description: str | None = None
    created_by: PydanticObjectId
    members: list[TeamMember] = []
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    class Settings:
        name = "teams"
        indexes = [IndexModel([("workspace_id", ASCENDING)])]

import enum
from datetime import datetime, timezone

from beanie import Document, PydanticObjectId
from pydantic import BaseModel, Field
from pymongo import ASCENDING, IndexModel


def generate_avatar(full_name: str) -> str:
    """Generate avatar initials from full name."""
    if not full_name:
        return "?"
    parts = full_name.strip().split()
    if len(parts) >= 2:
        return (parts[0][0] + parts[-1][0]).upper()
    elif len(parts) == 1:
        return parts[0][:2].upper() if len(parts[0]) >= 2 else parts[0][0].upper()
    return "?"


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
    role: str = "member"
    avatar: str = Field(default="")
    is_active: bool = True
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    def __init__(self, **data):
        super().__init__(**data)
        # Auto-generate avatar if not provided
        if not self.avatar:
            self.avatar = generate_avatar(self.full_name)

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
        indexes = [
            IndexModel([("workspace_id", ASCENDING)]),
            IndexModel([("members.user_id", ASCENDING)]),
        ]

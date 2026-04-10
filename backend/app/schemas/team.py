from datetime import datetime

from pydantic import BaseModel, Field

from app.models.user import TeamRole, WorkspaceRole
from app.schemas.base import PyObjectId


# ── Workspace ──────────────────────────────────────────────────────────────────

class WorkspaceCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    slug: str = Field(min_length=2, max_length=100, pattern=r"^[a-z0-9\-]+$")


class WorkspaceResponse(BaseModel):
    model_config = {"from_attributes": True}

    id: PyObjectId
    name: str
    slug: str
    created_by: PyObjectId
    created_at: datetime


# ── Team ───────────────────────────────────────────────────────────────────────

class TeamCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    description: str | None = None


class TeamUpdate(BaseModel):
    name: str | None = Field(default=None, max_length=255)
    description: str | None = None


class TeamResponse(BaseModel):
    model_config = {"from_attributes": True}

    id: PyObjectId
    workspace_id: PyObjectId
    name: str
    description: str | None
    created_by: PyObjectId
    created_at: datetime


class TeamMemberAdd(BaseModel):
    user_id: str
    role: TeamRole = TeamRole.MEMBER


class TeamMemberUpdate(BaseModel):
    role: TeamRole


class TeamMemberResponse(BaseModel):
    model_config = {"from_attributes": True}

    team_id: PyObjectId
    user_id: PyObjectId
    role: TeamRole
    joined_at: datetime


class TeamOwnerInfo(BaseModel):
    id: PyObjectId
    email: str
    full_name: str


class TeamWithOwnerResponse(BaseModel):
    id: PyObjectId
    workspace_id: PyObjectId
    name: str
    description: str | None
    created_by: PyObjectId
    created_at: datetime
    owner: TeamOwnerInfo | None


class TeamMemberDetailResponse(BaseModel):
    user_id: PyObjectId
    email: str
    full_name: str
    role: TeamRole
    joined_at: datetime

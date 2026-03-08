from datetime import datetime

from pydantic import BaseModel, Field

from app.schemas.base import PyObjectId


class ProjectCreate(BaseModel):
    team_id: str
    name: str = Field(min_length=1, max_length=255)
    description: str | None = None


class ProjectUpdate(BaseModel):
    name: str | None = Field(default=None, max_length=255)
    description: str | None = None
    is_archived: bool | None = None


class ProjectResponse(BaseModel):
    model_config = {"from_attributes": True}

    id: PyObjectId
    team_id: PyObjectId
    name: str
    description: str | None
    is_archived: bool
    created_by: PyObjectId
    created_at: datetime
    updated_at: datetime

from datetime import datetime, timezone

from beanie import Document, PydanticObjectId
from pydantic import BaseModel, Field
from pymongo import ASCENDING, IndexModel


class ProjectMember(BaseModel):
    user_id: PydanticObjectId
    joined_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class Project(Document):
    team_id: PydanticObjectId
    owner_id: PydanticObjectId
    name: str
    description: str | None = None
    members: list[ProjectMember] = []
    is_archived: bool = False
    created_by: PydanticObjectId
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    class Settings:
        name = "projects"
        indexes = [
            IndexModel([("team_id", ASCENDING)]),
            IndexModel([("owner_id", ASCENDING)]),
            IndexModel([("members.user_id", ASCENDING)]),
            IndexModel([("created_by", ASCENDING)]),
            IndexModel([("is_archived", ASCENDING)]),
        ]

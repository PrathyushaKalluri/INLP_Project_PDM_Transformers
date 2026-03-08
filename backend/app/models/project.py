from datetime import datetime, timezone

from beanie import Document, PydanticObjectId
from pydantic import Field
from pymongo import ASCENDING, IndexModel


class Project(Document):
    team_id: PydanticObjectId
    name: str
    description: str | None = None
    is_archived: bool = False
    created_by: PydanticObjectId
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    class Settings:
        name = "projects"
        indexes = [IndexModel([("team_id", ASCENDING)])]

from datetime import datetime, timezone

from beanie import PydanticObjectId
from pydantic import BaseModel, Field

from app.models.user import User, Workspace, Team, WorkspaceRole, TeamRole, TeamMember
from app.schemas.base import PyObjectId


class AuthUserView(BaseModel):
    """Minimal user payload for login verification and response construction."""

    id: PyObjectId = Field(alias="_id")
    email: str
    hashed_password: str
    full_name: str
    role: str
    is_active: bool
    created_at: datetime


class UserRepository:
    @staticmethod
    async def get_by_id(id: str) -> User | None:
        try:
            return await User.get(PydanticObjectId(id))
        except Exception:
            return None

    @staticmethod
    async def get_by_email(email: str) -> User | None:
        return await User.find_one(User.email == email)

    @staticmethod
    async def get_auth_view_by_email(email: str) -> AuthUserView | None:
        return await User.find_one(
            User.email == email,
            projection_model=AuthUserView,
        )

    @staticmethod
    async def create(**kwargs) -> User:
        user = User(**kwargs)
        await user.insert()
        return user

    @staticmethod
    async def update(user: User, **kwargs) -> User:
        for k, v in kwargs.items():
            setattr(user, k, v)
        user.updated_at = datetime.now(timezone.utc)
        await user.save()
        return user

    @staticmethod
    async def find_by_name(name: str) -> User | None:
        """Case-insensitive exact match on full_name."""
        import re
        pattern = re.compile(f"^{re.escape(name)}$", re.IGNORECASE)
        return await User.find_one({"full_name": {"$regex": pattern}})

    @staticmethod
    async def find_by_email_prefix(prefix: str) -> User | None:
        """Case-insensitive prefix match on email (before the @ symbol)."""
        import re
        pattern = re.compile(f"^{re.escape(prefix)}", re.IGNORECASE)
        return await User.find_one({"email": {"$regex": pattern}})


class WorkspaceRepository:
    @staticmethod
    async def get_by_id(id: str) -> Workspace | None:
        try:
            return await Workspace.get(PydanticObjectId(id))
        except Exception:
            return None

    @staticmethod
    async def get_by_slug(slug: str) -> Workspace | None:
        return await Workspace.find_one(Workspace.slug == slug)

    @staticmethod
    async def list_for_user(user_id: PydanticObjectId) -> list[Workspace]:
        return await Workspace.find(
            {"members.user_id": user_id}
        ).to_list()

    @staticmethod
    async def create(**kwargs) -> Workspace:
        ws = Workspace(**kwargs)
        await ws.insert()
        return ws

    @staticmethod
    async def update(ws: Workspace, **kwargs) -> Workspace:
        for k, v in kwargs.items():
            setattr(ws, k, v)
        ws.updated_at = datetime.now(timezone.utc)
        await ws.save()
        return ws


# Repository pattern for Team document operations
# Implements database-level queries with support for pagination and search
# Uses member.user_id index for efficient membership lookups
class TeamRepository:
    @staticmethod
    async def get_by_id(id: str) -> Team | None:
        try:
            return await Team.get(PydanticObjectId(id))
        except Exception:
            return None

    @staticmethod
    async def list_for_workspace(workspace_id: PydanticObjectId) -> list[Team]:
        return await Team.find(Team.workspace_id == workspace_id).to_list()

    @staticmethod
    async def list_for_user(
        user_id: PydanticObjectId,
        *,
        search: str | None = None,
        skip: int = 0,
        limit: int = 50,
    ) -> list[Team]:
        query: dict = {"members.user_id": user_id}

        if search and search.strip():
            query["name"] = {
                "$regex": search.strip(),
                "$options": "i",
            }

        safe_skip = max(0, skip)
        safe_limit = max(1, min(limit, 100))

        return (
            await Team.find(query)
            .sort("name")
            .skip(safe_skip)
            .limit(safe_limit)
            .to_list()
        )

    @staticmethod
    async def create(**kwargs) -> Team:
        team = Team(**kwargs)
        await team.insert()
        return team

    @staticmethod
    async def update(team: Team, **kwargs) -> Team:
        for k, v in kwargs.items():
            setattr(team, k, v)
        team.updated_at = datetime.now(timezone.utc)
        await team.save()
        return team

    @staticmethod
    def get_member(team: Team, user_id: PydanticObjectId) -> TeamMember | None:
        return next((m for m in team.members if m.user_id == user_id), None)

    @staticmethod
    async def add_member(team: Team, user_id: PydanticObjectId, role: TeamRole) -> TeamMember:
        member = TeamMember(user_id=user_id, role=role)
        team.members.append(member)
        await team.save()
        return member

    @staticmethod
    async def remove_member(team: Team, user_id: PydanticObjectId) -> None:
        team.members = [m for m in team.members if m.user_id != user_id]
        await team.save()

    @staticmethod
    async def delete(team: Team) -> None:
        await team.delete()

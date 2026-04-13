from datetime import datetime, timezone
import re

from beanie import PydanticObjectId

from app.models.project import Project, ProjectMember


class ProjectRepository:
    @staticmethod
    async def get_by_id(id: str) -> Project | None:
        try:
            return await Project.get(PydanticObjectId(id))
        except Exception:
            return None

    @staticmethod
    async def list_for_team(
        team_id: PydanticObjectId,
        include_archived: bool = False,
        skip: int = 0,
        limit: int = 50,
    ) -> list[Project]:
        query = Project.find(Project.team_id == team_id)
        if not include_archived:
            query = query.find(Project.is_archived == False)  # noqa: E712
        return await query.skip(skip).limit(limit).to_list()

    @staticmethod
    async def count_for_team(team_id: PydanticObjectId, include_archived: bool = False) -> int:
        query = Project.find(Project.team_id == team_id)
        if not include_archived:
            query = query.find(Project.is_archived == False)  # noqa: E712
        return await query.count()

    @staticmethod
    async def list_for_user(
        user_id: PydanticObjectId,
        include_archived: bool = False,
        skip: int = 0,
        limit: int = 50,
    ) -> list[Project]:
        query = Project.find(
            {
                "$or": [
                    {"owner_id": user_id},
                    {"members.user_id": user_id},
                    {"created_by": user_id},
                ]
            }
        )
        if not include_archived:
            query = query.find(Project.is_archived == False)  # noqa: E712
        return await query.skip(skip).limit(limit).to_list()

    @staticmethod
    async def count_for_user(user_id: PydanticObjectId, include_archived: bool = False) -> int:
        query = Project.find(
            {
                "$or": [
                    {"owner_id": user_id},
                    {"members.user_id": user_id},
                    {"created_by": user_id},
                ]
            }
        )
        if not include_archived:
            query = query.find(Project.is_archived == False)  # noqa: E712
        return await query.count()

    @staticmethod
    async def list_ids_for_user(user_id: PydanticObjectId, include_archived: bool = False) -> list[PydanticObjectId]:
        projects = await ProjectRepository.list_for_user(
            user_id=user_id,
            include_archived=include_archived,
            skip=0,
            limit=5000,
        )
        return [p.id for p in projects]

    @staticmethod
    async def create(**kwargs) -> Project:
        project = Project(**kwargs)
        await project.insert()
        return project

    @staticmethod
    async def exists_team_name(
        team_id: PydanticObjectId,
        name: str,
        exclude_project_id: PydanticObjectId | None = None,
    ) -> bool:
        query: dict = {
            "team_id": team_id,
            "name": {"$regex": f"^{re.escape(name.strip())}$", "$options": "i"},
        }
        if exclude_project_id:
            query["_id"] = {"$ne": exclude_project_id}

        existing = await Project.find_one(query)
        return existing is not None

    @staticmethod
    async def update(project: Project, **kwargs) -> Project:
        for k, v in kwargs.items():
            setattr(project, k, v)
        project.updated_at = datetime.now(timezone.utc)
        await project.save()
        return project

    @staticmethod
    def get_member(project: Project, user_id: PydanticObjectId) -> ProjectMember | None:
        return next((m for m in project.members if m.user_id == user_id), None)

    @staticmethod
    async def add_member(project: Project, user_id: PydanticObjectId) -> ProjectMember:
        member = ProjectMember(user_id=user_id)
        project.members.append(member)
        project.updated_at = datetime.now(timezone.utc)
        await project.save()
        return member

    @staticmethod
    async def remove_member(project: Project, user_id: PydanticObjectId) -> None:
        project.members = [m for m in project.members if m.user_id != user_id]
        project.updated_at = datetime.now(timezone.utc)
        await project.save()

from datetime import datetime, timezone

from beanie import PydanticObjectId

from app.models.project import Project


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
    async def create(**kwargs) -> Project:
        project = Project(**kwargs)
        await project.insert()
        return project

    @staticmethod
    async def update(project: Project, **kwargs) -> Project:
        for k, v in kwargs.items():
            setattr(project, k, v)
        project.updated_at = datetime.now(timezone.utc)
        await project.save()
        return project

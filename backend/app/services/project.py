from beanie import PydanticObjectId

from app.models.project import Project
from app.repositories.project import ProjectRepository
from app.schemas.project import ProjectCreate, ProjectUpdate
from app.services.errors import forbidden, not_found
from app.services.team import TeamService


class ProjectService:
    def __init__(self) -> None:
        self.team_svc = TeamService()

    async def create(self, data: ProjectCreate, creator_id: PydanticObjectId) -> Project:
        team = await self.team_svc.get_or_404(data.team_id)
        if not await self.team_svc.is_member(team.id, creator_id):
            raise forbidden("You must be a team member to create a project.")
        return await ProjectRepository.create(
            team_id=team.id,
            name=data.name,
            description=data.description,
            created_by=creator_id,
        )

    async def get_or_404(self, project_id: str) -> Project:
        project = await ProjectRepository.get_by_id(project_id)
        if not project:
            raise not_found("Project")
        return project

    async def update(self, project_id: str, data: ProjectUpdate, requester_id: PydanticObjectId) -> Project:
        project = await self.get_or_404(project_id)
        await self._require_team_member(project.team_id, requester_id)
        return await ProjectRepository.update(project, **data.model_dump(exclude_none=True))

    async def list_for_team(
        self,
        team_id: str,
        requester_id: PydanticObjectId,
        include_archived: bool = False,
        skip: int = 0,
        limit: int = 50,
    ) -> tuple[list[Project], int]:
        team = await self.team_svc.get_or_404(team_id)
        if not await self.team_svc.is_member(team.id, requester_id):
            raise forbidden("You are not a member of this team.")
        team_oid = PydanticObjectId(team_id)
        projects = await ProjectRepository.list_for_team(team_oid, include_archived, skip, limit)
        total = await ProjectRepository.count_for_team(team_oid, include_archived)
        return projects, total

    async def _require_team_member(self, team_id: PydanticObjectId, user_id: PydanticObjectId) -> None:
        if not await self.team_svc.is_member(team_id, user_id):
            raise forbidden("You are not a member of this team.")

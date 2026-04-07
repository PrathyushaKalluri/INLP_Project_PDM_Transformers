from beanie import PydanticObjectId

from app.models.project import Project
from app.repositories.project import ProjectRepository
from app.repositories.user import UserRepository
from app.schemas.project import ProjectCreate, ProjectUpdate
from app.services.errors import conflict, forbidden, not_found
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
            owner_id=creator_id,
            name=data.name,
            description=data.description,
            members=[],
            created_by=creator_id,
        )

    async def get_or_404(self, project_id: str) -> Project:
        project = await ProjectRepository.get_by_id(project_id)
        if not project:
            raise not_found("Project")
        return project

    async def update(self, project_id: str, data: ProjectUpdate, requester_id: PydanticObjectId) -> Project:
        project = await self.get_or_404(project_id)
        self._require_project_owner(project, requester_id)
        return await ProjectRepository.update(project, **data.model_dump(exclude_none=True))

    async def list_for_user(
        self,
        requester_id: PydanticObjectId,
        include_archived: bool = False,
        skip: int = 0,
        limit: int = 50,
    ) -> tuple[list[Project], int]:
        projects = await ProjectRepository.list_for_user(
            user_id=requester_id,
            include_archived=include_archived,
            skip=skip,
            limit=limit,
        )
        total = await ProjectRepository.count_for_user(requester_id, include_archived)
        return projects, total

    async def list_ids_for_user(
        self,
        requester_id: PydanticObjectId,
        include_archived: bool = False,
    ) -> list[PydanticObjectId]:
        return await ProjectRepository.list_ids_for_user(requester_id, include_archived)

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

    async def _require_project_member(self, project_id: PydanticObjectId | str, user_id: PydanticObjectId) -> Project:
        project = await self.get_or_404(str(project_id))
        if self._is_project_member(project, user_id):
            return project
        raise forbidden("You are not a member of this project.")

    async def add_member(self, project_id: str, user_id: str, requester_id: PydanticObjectId) -> None:
        project = await self.get_or_404(project_id)
        self._require_project_owner(project, requester_id)

        target_user = await UserRepository.get_by_id(user_id)
        if not target_user:
            raise not_found("User")

        await self._require_team_member(project.team_id, target_user.id)

        if self._is_project_member(project, target_user.id):
            raise conflict("User is already a member of this project.")

        await ProjectRepository.add_member(project, target_user.id)

    async def remove_member(self, project_id: str, user_id: str, requester_id: PydanticObjectId) -> None:
        project = await self.get_or_404(project_id)
        self._require_project_owner(project, requester_id)
        target_oid = PydanticObjectId(user_id)

        if target_oid == project.owner_id:
            raise forbidden("Project owner cannot be removed from project members.")

        member = ProjectRepository.get_member(project, target_oid)
        if not member:
            raise not_found("Project member")

        await ProjectRepository.remove_member(project, target_oid)

    async def list_members(self, project_id: str, requester_id: PydanticObjectId):
        project = await self._require_project_member(project_id, requester_id)
        return project.members

    def _is_project_member(self, project: Project, user_id: PydanticObjectId) -> bool:
        owner_id = getattr(project, "owner_id", None)
        if owner_id and owner_id == user_id:
            return True
        if project.created_by == user_id:
            return True
        return ProjectRepository.get_member(project, user_id) is not None

    def _is_project_owner(self, project: Project, user_id: PydanticObjectId) -> bool:
        owner_id = getattr(project, "owner_id", None)
        if owner_id:
            return owner_id == user_id
        return project.created_by == user_id

    def _require_project_owner(self, project: Project, user_id: PydanticObjectId) -> None:
        if not self._is_project_owner(project, user_id):
            raise forbidden("Only project owner can perform this action.")

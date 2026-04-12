from beanie import PydanticObjectId

from app.models.user import Team, TeamRole, Workspace, WorkspaceMember, WorkspaceRole
from app.repositories.user import TeamRepository, UserRepository, WorkspaceRepository
from app.schemas.team import TeamCreate, TeamMemberAdd, TeamUpdate, WorkspaceCreate, TeamMemberUpdate
from app.services.errors import bad_request, conflict, forbidden, not_found


class WorkspaceService:
    async def create(self, data: WorkspaceCreate, creator_id: PydanticObjectId) -> Workspace:
        existing = await WorkspaceRepository.get_by_slug(data.slug)
        if existing:
            raise conflict(f"Workspace slug '{data.slug}' is already taken.")
        workspace = await WorkspaceRepository.create(
            name=data.name,
            slug=data.slug,
            created_by=creator_id,
            members=[WorkspaceMember(user_id=creator_id, role=WorkspaceRole.ADMIN)],
        )
        return workspace

    async def list_for_user(self, user_id: PydanticObjectId) -> list[Workspace]:
        return await WorkspaceRepository.list_for_user(user_id)

    async def get_or_404(self, workspace_id: str) -> Workspace:
        ws = await WorkspaceRepository.get_by_id(workspace_id)
        if not ws:
            raise not_found("Workspace")
        return ws

    def require_member(self, workspace: Workspace, user_id: PydanticObjectId) -> None:
        if not any(member.user_id == user_id for member in workspace.members):
            raise forbidden("You are not a member of this workspace.")


class TeamService:
    async def create(self, workspace_id: str, data: TeamCreate, creator_id: PydanticObjectId) -> Team:
        workspace_oid = PydanticObjectId(workspace_id)
        team = await TeamRepository.create(
            workspace_id=workspace_oid,
            name=data.name,
            description=data.description,
            created_by=creator_id,
            members=[],
        )
        await TeamRepository.add_member(team, creator_id, TeamRole.OWNER)
        return team

    async def update(self, team_id: str, data: TeamUpdate, requester_id: PydanticObjectId) -> Team:
        team = await self._get_or_404(team_id)
        self._require_owner(team, requester_id)
        return await TeamRepository.update(team, **data.model_dump(exclude_none=True))

    async def get_or_404(self, team_id: str) -> Team:
        return await self._get_or_404(team_id)

    async def list_for_workspace(self, workspace_id: str, requester_id: PydanticObjectId) -> list[Team]:
        ws = await WorkspaceService().get_or_404(workspace_id)
        WorkspaceService().require_member(ws, requester_id)
        return await TeamRepository.list_for_workspace(PydanticObjectId(workspace_id))

    async def list_for_user(
        self,
        user_id: PydanticObjectId,
        *,
        search: str | None = None,
        page: int = 1,
        limit: int = 50,
    ) -> list[Team]:
        safe_page = max(1, page)
        safe_limit = max(1, min(limit, 100))
        skip = (safe_page - 1) * safe_limit
        return await TeamRepository.list_for_user(
            user_id,
            search=search,
            skip=skip,
            limit=safe_limit,
        )

    async def add_member(
        self, team_id: str, data: TeamMemberAdd, requester_id: PydanticObjectId
    ) -> None:
        team = await self._get_or_404(team_id)
        self._require_owner(team, requester_id)
        target_user = await UserRepository.get_by_id(data.user_id)
        if not target_user:
            raise not_found("User")
        existing = TeamRepository.get_member(team, target_user.id)
        if existing:
            raise conflict("User is already a member of this team.")
        await TeamRepository.add_member(team, target_user.id, data.role)

    async def remove_member(
        self, team_id: str, user_id: str, requester_id: PydanticObjectId
    ) -> None:
        team = await self._get_or_404(team_id)
        self._require_owner(team, requester_id)
        target_oid = PydanticObjectId(user_id)
        member = TeamRepository.get_member(team, target_oid)
        if not member:
            raise not_found("Team member")
        await TeamRepository.remove_member(team, target_oid)

    async def update_member_role(
        self, team_id: str, user_id: str, data: TeamMemberUpdate, requester_id: PydanticObjectId
    ) -> None:
        team = await self._get_or_404(team_id)
        self._require_owner(team, requester_id)
        target_oid = PydanticObjectId(user_id)
        member = TeamRepository.get_member(team, target_oid)
        if not member:
            raise not_found("Team member")
        
        # Update the role
        member.role = data.role
        await TeamRepository.update(team)

    async def delete(self, team_id: str, requester_id: PydanticObjectId) -> None:
        team = await self._get_or_404(team_id)
        self._require_owner(team, requester_id)
        await TeamRepository.delete(team)

    async def list_for_workspace_with_owners(
        self,
        workspace_id: str,
        requester_id: PydanticObjectId,
    ) -> list[dict]:
        from app.schemas.team import TeamOwnerInfo, TeamWithOwnerResponse

        ws = await WorkspaceService().get_or_404(workspace_id)
        WorkspaceService().require_member(ws, requester_id)
        teams = await TeamRepository.list_for_workspace(PydanticObjectId(workspace_id))
        result = []
        for team in teams:
            owner_member = next(
                (m for m in team.members if m.role == TeamRole.OWNER), None
            )
            owner_info = None
            if owner_member:
                owner_user = await UserRepository.get_by_id(str(owner_member.user_id))
                if owner_user:
                    owner_info = TeamOwnerInfo(
                        id=str(owner_user.id),
                        email=owner_user.email,
                        full_name=owner_user.full_name,
                    )
            result.append(
                TeamWithOwnerResponse(
                    id=str(team.id),
                    workspace_id=str(team.workspace_id),
                    name=team.name,
                    description=team.description,
                    created_by=str(team.created_by),
                    created_at=team.created_at,
                    owner=owner_info,
                )
            )
        return result

    async def list_members_detail(self, team_id: str, requester_id: PydanticObjectId) -> list[dict]:
        from app.schemas.team import TeamMemberDetailResponse

        team = await self._get_or_404(team_id)
        if not TeamRepository.get_member(team, requester_id):
            raise forbidden("You are not a member of this team.")
        result = []
        for member in team.members:
            user = await UserRepository.get_by_id(str(member.user_id))
            if user:
                result.append(
                    TeamMemberDetailResponse(
                        user_id=str(user.id),
                        email=user.email,
                        full_name=user.full_name,
                        role=member.role,
                        joined_at=member.joined_at,
                    )
                )
        return result

    async def is_member(self, team_id: PydanticObjectId | str, user_id: PydanticObjectId) -> bool:
        team_id_str = str(team_id)
        team = await TeamRepository.get_by_id(team_id_str)
        if not team:
            return False
        return TeamRepository.get_member(team, user_id) is not None

    async def _get_or_404(self, team_id: str) -> Team:
        team = await TeamRepository.get_by_id(team_id)
        if not team:
            raise not_found("Team")
        return team

    def _require_owner(self, team: Team, user_id: PydanticObjectId) -> None:
        member = TeamRepository.get_member(team, user_id)
        if not member or member.role != TeamRole.OWNER:
            raise forbidden("Only team owners can perform this action.")

from fastapi import APIRouter, Depends, Query

from app.api.deps import get_current_user
from app.models.user import User
from app.schemas.team import (
    TeamCreate, TeamMemberAdd, TeamMemberDetailResponse, TeamMemberResponse,
    TeamResponse, TeamUpdate, TeamWithOwnerResponse, TeamMemberUpdate,
    WorkspaceCreate, WorkspaceResponse,
)
from app.services.team import TeamService, WorkspaceService

router = APIRouter(tags=["Teams & Workspaces"])


# ── Workspaces ─────────────────────────────────────────────────────────────────

# ── Teams & Workspaces API Endpoints ──
# Supports full team management including pagination and search for scalable UX
# See: kanban-app/lib/teams.ts for frontend client integration

@router.post("/workspaces", response_model=WorkspaceResponse, status_code=201)
async def create_workspace(
    data: WorkspaceCreate,
    current_user: User = Depends(get_current_user),
):
    svc = WorkspaceService()
    return await svc.create(data, current_user.id)


@router.get("/workspaces", response_model=list[WorkspaceResponse])
async def list_my_workspaces(
    current_user: User = Depends(get_current_user),
):
    svc = WorkspaceService()
    return await svc.list_for_user(current_user.id)


@router.get("/workspaces/default", response_model=WorkspaceResponse)
async def get_or_create_default_workspace(
    current_user: User = Depends(get_current_user),
):
    """
    Get or create a default workspace for the current user.
    This ensures users always have at least one workspace to work with.
    """
    svc = WorkspaceService()
    
    # Try to get user's first workspace
    workspaces = await svc.list_for_user(current_user.id)
    if workspaces:
        return workspaces[0]
    
    # If no workspace exists, create one for the user
    default_workspace_data = WorkspaceCreate(
        name=f"{current_user.full_name}'s Workspace",
        slug=f"{current_user.full_name.lower().replace(' ', '-')}-workspace"
    )
    return await svc.create(default_workspace_data, current_user.id)


@router.get("/workspaces/{workspace_id}", response_model=WorkspaceResponse)
async def get_workspace(
    workspace_id: str,
    current_user: User = Depends(get_current_user),
):
    svc = WorkspaceService()
    workspace = await svc.get_or_404(workspace_id)
    svc.require_member(workspace, current_user.id)
    return workspace


# ── Teams ──────────────────────────────────────────────────────────────────────

@router.post("/workspaces/{workspace_id}/teams", response_model=TeamResponse, status_code=201)
async def create_team(
    workspace_id: str,
    data: TeamCreate,
    current_user: User = Depends(get_current_user),
):
    svc = TeamService()
    return await svc.create(workspace_id, data, current_user.id)


@router.get("/workspaces/{workspace_id}/teams/with-owners", response_model=list[TeamWithOwnerResponse])
async def list_teams_with_owners(
    workspace_id: str,
    current_user: User = Depends(get_current_user),
):
    """List all teams in a workspace, each with their owner's full profile embedded."""
    svc = TeamService()
    return await svc.list_for_workspace_with_owners(workspace_id, current_user.id)


@router.get("/workspaces/{workspace_id}/teams", response_model=list[TeamResponse])
async def list_teams(
    workspace_id: str,
    current_user: User = Depends(get_current_user),
):
    svc = TeamService()
    return await svc.list_for_workspace(workspace_id, current_user.id)


@router.get("/teams", response_model=list[TeamResponse])
async def list_my_teams(
    current_user: User = Depends(get_current_user),
    page: int = Query(1, ge=1),
    limit: int = Query(50, ge=1, le=100),
    search: str | None = Query(default=None),
):
    svc = TeamService()
    return await svc.list_for_user(
        current_user.id,
        page=page,
        limit=limit,
        search=search,
    )


@router.get("/teams/{team_id}", response_model=TeamResponse)
async def get_team(
    team_id: str,
    current_user: User = Depends(get_current_user),
):
    svc = TeamService()
    return await svc.get_or_404(team_id)


@router.patch("/teams/{team_id}", response_model=TeamResponse)
async def update_team(
    team_id: str,
    data: TeamUpdate,
    current_user: User = Depends(get_current_user),
):
    svc = TeamService()
    return await svc.update(team_id, data, current_user.id)


@router.delete("/teams/{team_id}", status_code=204)
async def delete_team(
    team_id: str,
    current_user: User = Depends(get_current_user),
):
    """Delete a team. Only team owners can delete teams."""
    svc = TeamService()
    await svc.delete(team_id, current_user.id)


@router.get("/teams/{team_id}/members", response_model=list[TeamMemberDetailResponse])
async def list_team_members(
    team_id: str,
    current_user: User = Depends(get_current_user),
):
    """List all members of a team with their user profile and role."""
    svc = TeamService()
    return await svc.list_members_detail(team_id, current_user.id)


@router.post("/teams/{team_id}/members", status_code=204)
async def add_team_member(
    team_id: str,
    data: TeamMemberAdd,
    current_user: User = Depends(get_current_user),
):
    svc = TeamService()
    await svc.add_member(team_id, data, current_user.id)


@router.delete("/teams/{team_id}/members/{user_id}", status_code=204)
async def remove_team_member(
    team_id: str,
    user_id: str,
    current_user: User = Depends(get_current_user),
):
    svc = TeamService()
    await svc.remove_member(team_id, user_id, current_user.id)


@router.patch("/teams/{team_id}/members/{user_id}", status_code=204)
async def update_team_member_role(
    team_id: str,
    user_id: str,
    data: TeamMemberUpdate,
    current_user: User = Depends(get_current_user),
):
    """Update a team member's role. Only team owners can update roles."""
    svc = TeamService()
    await svc.update_member_role(team_id, user_id, data, current_user.id)

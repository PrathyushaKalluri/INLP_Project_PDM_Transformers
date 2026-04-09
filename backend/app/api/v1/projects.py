from fastapi import APIRouter, Depends, Query

from app.api.deps import get_current_user
from app.models.user import User
from app.schemas.project import (
    ProjectCreate,
    ProjectMemberAdd,
    ProjectMemberResponse,
    ProjectResponse,
    ProjectUpdate,
)
from app.services.project import ProjectService

router = APIRouter(prefix="/projects", tags=["Projects"])


@router.post("", response_model=ProjectResponse, status_code=201)
async def create_project(
    data: ProjectCreate,
    current_user: User = Depends(get_current_user),
):
    svc = ProjectService()
    return await svc.create(data, current_user.id)


@router.get("", response_model=dict)
async def list_projects(
    include_archived: bool = Query(False),
    page: int = Query(1, ge=1),
    limit: int = Query(50, ge=1, le=200),
    current_user: User = Depends(get_current_user),
):
    svc = ProjectService()
    skip = (page - 1) * limit
    projects, total = await svc.list_for_user(
        current_user.id,
        include_archived,
        skip,
        limit,
    )
    return {
        "total": total,
        "page": page,
        "limit": limit,
        "items": [ProjectResponse.model_validate(p) for p in projects],
    }


@router.get("/{project_id}", response_model=ProjectResponse)
async def get_project(
    project_id: str,
    current_user: User = Depends(get_current_user),
):
    svc = ProjectService()
    return await svc._require_project_member(project_id, current_user.id)


@router.patch("/{project_id}", response_model=ProjectResponse)
async def update_project(
    project_id: str,
    data: ProjectUpdate,
    current_user: User = Depends(get_current_user),
):
    svc = ProjectService()
    return await svc.update(project_id, data, current_user.id)


@router.delete("/{project_id}", status_code=204)
async def delete_project(
    project_id: str,
    current_user: User = Depends(get_current_user),
):
    svc = ProjectService()
    await svc.delete(project_id, current_user.id)


@router.get("/{project_id}/members", response_model=list[ProjectMemberResponse])
async def list_project_members(
    project_id: str,
    current_user: User = Depends(get_current_user),
):
    svc = ProjectService()
    return await svc.list_members(project_id, current_user.id)


@router.post("/{project_id}/members", status_code=204)
async def add_project_member(
    project_id: str,
    data: ProjectMemberAdd,
    current_user: User = Depends(get_current_user),
):
    svc = ProjectService()
    await svc.add_member(project_id, data.user_id, current_user.id)


@router.delete("/{project_id}/members/{user_id}", status_code=204)
async def remove_project_member(
    project_id: str,
    user_id: str,
    current_user: User = Depends(get_current_user),
):
    svc = ProjectService()
    await svc.remove_member(project_id, user_id, current_user.id)

from datetime import date

from fastapi import APIRouter, Depends, Query

from app.api.deps import get_current_user
from app.models.task import SuggestionReviewStatus, TaskPriority, TaskStatus
from app.models.user import User
from app.schemas.task import (
    SubTaskCreate, SubTaskResponse, SubTaskUpdate,
    SuggestionApproveRequest, SuggestionReviewUpdate, TaskSuggestionResponse,
    TaskCreate, TaskEvidenceResponse, TaskNoteCreate, TaskNoteResponse,
    TaskResponse, TaskStatusHistoryResponse, TaskUpdate,
)
from app.services.task import TaskService

router = APIRouter(prefix="/tasks", tags=["Tasks"])


# ── Task CRUD ──────────────────────────────────────────────────────────────────

@router.post("", response_model=TaskResponse, status_code=201)
async def create_task(
    data: TaskCreate,
    current_user: User = Depends(get_current_user),
):
    svc = TaskService()
    return await svc.create_manual(data, current_user.id)


@router.get("", response_model=dict)
async def list_tasks(
    project_id: str | None = Query(None),
    team_id: str | None = Query(None),
    meeting_id: str | None = Query(None),
    assignee_id: str | None = Query(None),
    owner_id: str | None = Query(None),
    status: TaskStatus | None = Query(None),
    priority: TaskPriority | None = Query(None),
    is_manual: bool | None = Query(None),
    due_before: date | None = Query(None),
    due_after: date | None = Query(None),
    page: int = Query(1, ge=1),
    limit: int = Query(50, ge=1, le=200),
    sort_by: str = Query("created_at"),
    sort_order: str = Query("desc", pattern="^(asc|desc)$"),
    current_user: User = Depends(get_current_user),
):
    svc = TaskService()
    skip = (page - 1) * limit
    tasks, total = await svc.list_filtered(
        requester_id=current_user.id,
        project_id=project_id,
        team_id=team_id,
        meeting_id=meeting_id,
        assignee_id=assignee_id,
        owner_id=owner_id,
        status=status,
        priority=priority,
        is_manual=is_manual,
        due_before=due_before,
        due_after=due_after,
        skip=skip,
        limit=limit,
        sort_by=sort_by,
        sort_order=sort_order,
    )
    return {
        "total": total,
        "page": page,
        "limit": limit,
        "items": [TaskResponse.model_validate(t) for t in tasks],
    }


@router.get("/{task_id}", response_model=TaskResponse)
async def get_task(
    task_id: str,
    current_user: User = Depends(get_current_user),
):
    svc = TaskService()
    task = await svc.get_or_404(task_id)
    await svc.project_svc._require_team_member(task.team_id, current_user.id)
    return task


@router.patch("/{task_id}", response_model=TaskResponse)
async def update_task(
    task_id: str,
    data: TaskUpdate,
    current_user: User = Depends(get_current_user),
):
    svc = TaskService()
    return await svc.update(task_id, data, current_user.id)


@router.delete("/{task_id}", status_code=204)
async def delete_task(
    task_id: str,
    current_user: User = Depends(get_current_user),
):
    svc = TaskService()
    await svc.delete(task_id, current_user.id)


# ── Evidence ───────────────────────────────────────────────────────────────────

@router.get("/{task_id}/evidence", response_model=list[TaskEvidenceResponse])
async def get_evidence(
    task_id: str,
    current_user: User = Depends(get_current_user),
):
    svc = TaskService()
    return await svc.get_evidence(task_id, current_user.id)


# ── SubTasks ───────────────────────────────────────────────────────────────────

@router.get("/{task_id}/subtasks", response_model=list[SubTaskResponse])
async def list_subtasks(
    task_id: str,
    current_user: User = Depends(get_current_user),
):
    svc = TaskService()
    return await svc.get_subtasks(task_id, current_user.id)


@router.post("/{task_id}/subtasks", response_model=SubTaskResponse, status_code=201)
async def create_subtask(
    task_id: str,
    data: SubTaskCreate,
    current_user: User = Depends(get_current_user),
):
    svc = TaskService()
    return await svc.create_subtask(task_id, data, current_user.id)


@router.patch("/{task_id}/subtasks/{subtask_id}", response_model=SubTaskResponse)
async def update_subtask(
    task_id: str,
    subtask_id: str,
    data: SubTaskUpdate,
    current_user: User = Depends(get_current_user),
):
    svc = TaskService()
    return await svc.update_subtask(task_id, subtask_id, data, current_user.id)


# ── Notes ──────────────────────────────────────────────────────────────────────

@router.get("/{task_id}/notes", response_model=list[TaskNoteResponse])
async def list_notes(
    task_id: str,
    current_user: User = Depends(get_current_user),
):
    svc = TaskService()
    return await svc.get_notes(task_id, current_user.id)


@router.post("/{task_id}/notes", response_model=TaskNoteResponse, status_code=201)
async def create_note(
    task_id: str,
    data: TaskNoteCreate,
    current_user: User = Depends(get_current_user),
):
    svc = TaskService()
    return await svc.create_note(task_id, data, current_user.id)


# ── Status History ─────────────────────────────────────────────────────────────

@router.get("/{task_id}/history", response_model=list[TaskStatusHistoryResponse])
async def get_status_history(
    task_id: str,
    current_user: User = Depends(get_current_user),
):
    svc = TaskService()
    return await svc.get_status_history(task_id, current_user.id)


# ── Suggestion Review ──────────────────────────────────────────────────────────

@router.patch("/suggestions/{suggestion_id}", response_model=TaskSuggestionResponse)
async def update_suggestion(
    suggestion_id: str,
    data: SuggestionReviewUpdate,
    current_user: User = Depends(get_current_user),
):
    svc = TaskService()
    return await svc.update_suggestion(suggestion_id, data, current_user.id)


@router.post("/suggestions/{suggestion_id}/approve", response_model=TaskResponse, status_code=201)
async def approve_suggestion(
    suggestion_id: str,
    data: SuggestionApproveRequest,
    current_user: User = Depends(get_current_user),
):
    svc = TaskService()
    return await svc.approve_suggestion(suggestion_id, data, current_user.id)


@router.post("/suggestions/{suggestion_id}/reject", response_model=TaskSuggestionResponse)
async def reject_suggestion(
    suggestion_id: str,
    current_user: User = Depends(get_current_user),
):
    svc = TaskService()
    return await svc.reject_suggestion(suggestion_id, current_user.id)


from fastapi import APIRouter, BackgroundTasks, Depends, File, Query, UploadFile

from app.api.deps import get_current_user
from app.core.config import settings
from app.models.user import User
from app.schemas.meeting import (
    MeetingCreate, MeetingResponse, MeetingSummaryResponse,
    MeetingUpdate, TranscriptStatusResponse,
)
from app.schemas.task import TaskSuggestionResponse
from app.services.errors import bad_request
from app.services.meeting import MeetingService
from app.services.task import TaskService
from app.models.task import SuggestionReviewStatus

router = APIRouter(prefix="/meetings", tags=["Meetings"])


@router.post("", response_model=MeetingResponse, status_code=201)
async def create_meeting(
    data: MeetingCreate,
    current_user: User = Depends(get_current_user),
):
    svc = MeetingService()
    return await svc.create(data, current_user.id)


@router.get("", response_model=list[MeetingResponse])
async def list_meetings(
    project_id: str | None = Query(None),
    team_id: str | None = Query(None),
    page: int = Query(1, ge=1),
    limit: int = Query(50, ge=1, le=200),
    current_user: User = Depends(get_current_user),
):
    svc = MeetingService()
    skip = (page - 1) * limit
    if project_id:
        return await svc.list_for_project(project_id, current_user.id, skip, limit)
    elif team_id:
        return await svc.list_for_team(team_id, current_user.id, skip, limit)
    raise bad_request("Provide either project_id or team_id query parameter.")


@router.get("/{meeting_id}", response_model=MeetingResponse)
async def get_meeting(
    meeting_id: str,
    current_user: User = Depends(get_current_user),
):
    svc = MeetingService()
    return await svc.get_or_404(meeting_id)


@router.patch("/{meeting_id}", response_model=MeetingResponse)
async def update_meeting(
    meeting_id: str,
    data: MeetingUpdate,
    current_user: User = Depends(get_current_user),
):
    svc = MeetingService()
    return await svc.update(meeting_id, data, current_user.id)


@router.post("/{meeting_id}/transcript", response_model=TranscriptStatusResponse, status_code=202)
async def upload_transcript(
    meeting_id: str,
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
):
    if not file.filename or not file.filename.endswith(".txt"):
        raise bad_request("Only .txt transcript files are accepted.")

    content = await file.read()
    if len(content) > settings.max_upload_bytes:
        raise bad_request(f"File exceeds maximum size of {settings.MAX_UPLOAD_SIZE_MB}MB.")

    transcript_text = content.decode("utf-8", errors="replace")
    svc = MeetingService()
    transcript = await svc.upload_transcript(
        meeting_id, transcript_text, file.filename, current_user.id
    )
    background_tasks.add_task(_process_transcript, str(transcript.id))
    return transcript


async def _process_transcript(transcript_id: str) -> None:
    """Background task: no session needed — Beanie uses the app-level Motor client."""
    svc = MeetingService()
    await svc.process_transcript(transcript_id)


@router.get("/{meeting_id}/transcript/status", response_model=TranscriptStatusResponse)
async def get_transcript_status(
    meeting_id: str,
    current_user: User = Depends(get_current_user),
):
    svc = MeetingService()
    return await svc.get_transcript_status(meeting_id)


@router.get("/{meeting_id}/summary", response_model=MeetingSummaryResponse)
async def get_meeting_summary(
    meeting_id: str,
    current_user: User = Depends(get_current_user),
):
    svc = MeetingService()
    return await svc.get_summary(meeting_id)


@router.get("/{meeting_id}/suggestions", response_model=list[TaskSuggestionResponse])
async def list_suggestions(
    meeting_id: str,
    status: SuggestionReviewStatus | None = Query(None),
    current_user: User = Depends(get_current_user),
):
    svc = TaskService()
    return await svc.get_suggestions_for_meeting(meeting_id, current_user.id, status)


@router.get("/{meeting_id}/tasks", response_model=list)
async def list_meeting_tasks(
    meeting_id: str,
    current_user: User = Depends(get_current_user),
):
    from app.schemas.task import TaskResponse
    svc = TaskService()
    tasks, _ = await svc.list_filtered(
        requester_id=current_user.id, meeting_id=meeting_id, limit=200
    )
    return [TaskResponse.model_validate(t) for t in tasks]

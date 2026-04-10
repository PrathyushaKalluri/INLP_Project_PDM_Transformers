from fastapi import APIRouter, BackgroundTasks, Depends, File, Query, UploadFile
import time
import logging

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

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/meetings", tags=["Meetings"])


@router.post("", response_model=MeetingResponse, status_code=201)
async def create_meeting(
    data: MeetingCreate,
    current_user: User = Depends(get_current_user),
):
    svc = MeetingService()
    return await svc.create(data, current_user.id)


@router.get("", response_model=dict | list[MeetingResponse])
async def list_meetings(
    project_id: str | None = Query(None),
    team_id: str | None = Query(None),
    page: int = Query(1, ge=1),
    limit: int = Query(50, ge=1, le=200),
    paginated: bool = Query(False),
    current_user: User = Depends(get_current_user),
):
    svc = MeetingService()
    skip = (page - 1) * limit
    meetings = []
    count = 0
    if project_id:
        meetings, count = await svc.list_for_project(project_id, current_user.id, skip, limit)
    elif team_id:
        meetings, count = await svc.list_for_team(team_id, current_user.id, skip, limit)
    else:
        raise bad_request("Provide either project_id or team_id query parameter.")

    if paginated:
        return {
            "total": count,
            "page": page,
            "limit": limit,
            "items": [MeetingResponse.model_validate(m) for m in meetings],
        }
    return meetings


@router.get("/{meeting_id}", response_model=MeetingResponse)
async def get_meeting(
    meeting_id: str,
    current_user: User = Depends(get_current_user),
):
    svc = MeetingService()
    meeting = await svc.get_or_404(meeting_id)
    await svc.project_svc._require_project_member(meeting.project_id, current_user.id)
    return meeting


@router.patch("/{meeting_id}", response_model=MeetingResponse)
async def update_meeting(
    meeting_id: str,
    data: MeetingUpdate,
    current_user: User = Depends(get_current_user),
):
    svc = MeetingService()
    return await svc.update(meeting_id, data, current_user.id)


@router.delete("/{meeting_id}", status_code=204)
async def delete_meeting(
    meeting_id: str,
    current_user: User = Depends(get_current_user),
):
    svc = MeetingService()
    await svc.delete(meeting_id, current_user.id)


@router.post("/{meeting_id}/transcript", response_model=TranscriptStatusResponse, status_code=202)
async def upload_transcript(
    meeting_id: str,
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
):
    logger.info(f"[API_TRANSCRIPT] Transcript upload started for meeting {meeting_id}, file: {file.filename}")
    
    if not file.filename or not file.filename.endswith(".txt"):
        logger.warning(f"[API_TRANSCRIPT] Invalid file type: {file.filename}")
        raise bad_request("Only .txt transcript files are accepted.")

    content = await file.read()
    if len(content) > settings.max_upload_bytes:
        logger.warning(f"[API_TRANSCRIPT] File too large: {len(content)} bytes")
        raise bad_request(f"File exceeds maximum size of {settings.MAX_UPLOAD_SIZE_MB}MB.")

    transcript_text = content.decode("utf-8", errors="replace")
    logger.debug(f"[API_TRANSCRIPT] Transcript text decoded, length: {len(transcript_text)}")
    
    svc = MeetingService()
    transcript = await svc.upload_transcript(
        meeting_id, transcript_text, file.filename, current_user.id
    )
    logger.info(f"[API_TRANSCRIPT] Transcript created with ID {transcript.id}, scheduling background processing...")
    
    background_tasks.add_task(_process_transcript, str(transcript.id))
    logger.info(f"[API_TRANSCRIPT] Background processing task scheduled")
    
    return transcript


async def _process_transcript(transcript_id: str) -> None:
    """Background task: no session needed — Beanie uses the app-level Motor client."""
    try:
        logger.info(f"[BG_PROCESS] Starting background transcript processing for {transcript_id}")
        svc = MeetingService()
        await svc.process_transcript(transcript_id)
        logger.info(f"[BG_PROCESS] ✓ Background processing completed for {transcript_id}")
    except Exception as e:
        logger.error(f"[BG_PROCESS] ✗ Background processing failed for {transcript_id}: {e}", exc_info=True)


@router.get("/{meeting_id}/transcript/status", response_model=TranscriptStatusResponse)
async def get_transcript_status(
    meeting_id: str,
    current_user: User = Depends(get_current_user),
):
    svc = MeetingService()
    meeting = await svc.get_or_404(meeting_id)
    await svc.project_svc._require_project_member(meeting.project_id, current_user.id)
    return await svc.get_transcript_status(meeting_id)


@router.delete("/{meeting_id}/transcript", status_code=204)
async def delete_transcript(
    meeting_id: str,
    current_user: User = Depends(get_current_user),
):
    svc = MeetingService()
    transcript = await svc.get_transcript_status(meeting_id)
    await svc.delete_transcript(str(transcript.id), current_user.id)


@router.get("/{meeting_id}/summary", response_model=MeetingSummaryResponse)
async def get_meeting_summary(
    meeting_id: str,
    current_user: User = Depends(get_current_user),
):
    start_time = time.time()
    logger.info(f"[API_SUMMARY] GET summary request for meeting {meeting_id}")
    
    svc = MeetingService()
    try:
        meeting = await svc.get_or_404(meeting_id)
        logger.debug(f"[API_SUMMARY] Meeting found, checking access...")
        await svc.project_svc._require_project_member(meeting.project_id, current_user.id)
        
        logger.debug(f"[API_SUMMARY] Fetching summary...")
        summary = await svc.get_summary(meeting_id)
        
        elapsed = time.time() - start_time
        logger.info(f"[API_SUMMARY] ✓ Summary returned in {elapsed:.3f}s")
        return summary
    except Exception as e:
        elapsed = time.time() - start_time
        logger.error(f"[API_SUMMARY] ✗ Failed to get summary: {str(e)} ({elapsed:.3f}s)", exc_info=True)
        raise


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

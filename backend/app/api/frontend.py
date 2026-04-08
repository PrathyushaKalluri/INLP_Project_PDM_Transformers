import logging
from datetime import datetime

logger = logging.getLogger(__name__)

from app.models.processing import JOB_TOTAL_STEPS

from beanie import PydanticObjectId
from fastapi import APIRouter, Body, Depends, Query, WebSocket, WebSocketDisconnect

from app.api.deps import get_current_user
from app.core.realtime import realtime_hub
from app.core.security import decode_token
from app.models.meeting import Transcript
from app.models.notification import NotificationType
from app.models.task import TaskEvidence, TaskPriority, TaskStatus
from app.models.user import User
from app.repositories.meeting import MeetingRepository, MeetingSummaryRepository, TranscriptRepository
from app.repositories.user import UserRepository
from app.schemas.frontend import (
    AuthSignupRequest,
    FrontendAddParticipant,
    FrontendProjectCreate,
    FrontendProjectUpdate,
    FrontendPublishRequest,
    FrontendStartProcessingRequest,
    FrontendTaskCreate,
    FrontendTaskUpdate,
    FrontendTranscriptCreate,
    NotificationsReadRequest,
)
from app.schemas.meeting import MeetingCreate
from app.schemas.task import TaskCreate, TaskUpdate
from app.schemas.user import LoginRequest, UserCreate
from app.services.auth import AuthService
from app.services.errors import bad_request
from app.services.meeting import MeetingService
from app.services.notification import NotificationService
from app.services.processing import ProcessingService
from app.services.project import ProjectService
from app.services.task import TaskService

router = APIRouter(tags=["Frontend Adapter"])


def _project_to_frontend(project) -> dict:
    return {
        "id": str(project.id),
        "teamId": str(project.team_id),
        "ownerId": str(project.owner_id),
        "name": project.name,
        "description": project.description,
        "participantIds": [str(member.user_id) for member in project.members],
        "isArchived": project.is_archived,
        "createdBy": str(project.created_by),
        "createdAt": project.created_at.isoformat(),
        "updatedAt": project.updated_at.isoformat(),
    }


def _task_to_frontend(task) -> dict:
    return {
        "id": str(task.id),
        "projectId": str(task.project_id),
        "teamId": str(task.team_id),
        "meetingId": str(task.meeting_id) if task.meeting_id else None,
        "title": task.title,
        "description": task.description,
        "status": task.status.value,
        "priority": task.priority.value,
        "assigneeIds": [str(task.assignee_id)] if task.assignee_id else [],
        "ownerId": str(task.owner_id) if task.owner_id else None,
        "deadline": task.due_date.isoformat() if task.due_date else None,
        "createdAt": task.created_at.isoformat(),
        "updatedAt": task.updated_at.isoformat(),
    }


def _transcript_to_frontend(transcript: Transcript) -> dict:
    return {
        "id": str(transcript.id),
        "meetingId": str(transcript.meeting_id),
        "processingStatus": transcript.processing_status.value,
        "errorMessage": transcript.error_message,
        "createdAt": transcript.created_at.isoformat(),
        "processedAt": transcript.processed_at.isoformat() if transcript.processed_at else None,
        "text": transcript.raw_text,
    }


def _notification_to_frontend(note) -> dict:
    return {
        "id": str(note.id),
        "message": note.message,
        "type": note.type.value,
        "read": note.read,
        "createdAt": note.created_at.isoformat(),
    }


@router.post("/auth/signup")
async def frontend_signup(data: AuthSignupRequest):
    svc = AuthService()
    user = await svc.register(
        UserCreate(email=data.email, password=data.password, full_name=data.full_name)
    )
    return {
        "id": str(user.id),
        "email": user.email,
        "fullName": user.full_name,
    }


@router.post("/auth/login")
async def frontend_login(data: LoginRequest):
    svc = AuthService()
    token = await svc.login(data.email, data.password)
    user = await UserRepository.get_by_email(data.email)
    return {
        "user": {
            "id": str(user.id),
            "email": user.email,
            "fullName": user.full_name,
            "isActive": user.is_active,
        },
        "token": token.access_token,
        "refreshToken": token.refresh_token,
    }


@router.post("/auth/logout")
async def frontend_logout(current_user: User = Depends(get_current_user)):
    return {"success": True}


@router.get("/auth/me")
async def frontend_me(current_user: User = Depends(get_current_user)):
    return {
        "id": str(current_user.id),
        "email": current_user.email,
        "fullName": current_user.full_name,
        "isActive": current_user.is_active,
    }


@router.get("/projects")
async def frontend_projects(current_user: User = Depends(get_current_user)):
    svc = ProjectService()
    projects, _ = await svc.list_for_user(current_user.id, include_archived=False, skip=0, limit=1000)
    return [_project_to_frontend(p) for p in projects]


@router.post("/projects")
async def frontend_create_project(data: FrontendProjectCreate, current_user: User = Depends(get_current_user)):
    svc = ProjectService()
    project = await svc.create(data, current_user.id)
    return _project_to_frontend(project)


@router.patch("/projects/{project_id}")
async def frontend_update_project(
    project_id: str,
    data: FrontendProjectUpdate,
    current_user: User = Depends(get_current_user),
):
    svc = ProjectService()
    project = await svc.update(project_id, data, current_user.id)
    return _project_to_frontend(project)


@router.get("/projects/{project_id}")
async def frontend_get_project(project_id: str, current_user: User = Depends(get_current_user)):
    svc = ProjectService()
    project = await svc._require_project_member(project_id, current_user.id)
    return _project_to_frontend(project)


@router.delete("/projects/{project_id}", status_code=204)
async def frontend_delete_project(project_id: str, current_user: User = Depends(get_current_user)):
    svc = ProjectService()
    await svc.delete(project_id, current_user.id)


@router.post("/projects/{project_id}/participants", status_code=204)
async def frontend_add_participant(
    project_id: str,
    data: FrontendAddParticipant,
    current_user: User = Depends(get_current_user),
):
    svc = ProjectService()
    await svc.add_member(project_id, data.user_id, current_user.id)


@router.get("/tasks")
async def frontend_list_tasks(
    projectId: str | None = Query(None),
    current_user: User = Depends(get_current_user),
):
    svc = TaskService()
    tasks, _ = await svc.list_filtered(requester_id=current_user.id, project_id=projectId, limit=1000)
    return [_task_to_frontend(task) for task in tasks]


@router.post("/tasks")
async def frontend_create_task(data: FrontendTaskCreate, current_user: User = Depends(get_current_user)):
    svc = TaskService()
    payload = TaskCreate(
        project_id=data.project_id,
        title=data.title,
        description=data.description,
        assignee_id=data.assignee_ids[0] if data.assignee_ids else None,
        owner_id=data.owner_id,
        due_date=data.deadline,
    )
    task = await svc.create_manual(payload, current_user.id)
    return _task_to_frontend(task)


@router.patch("/tasks/{task_id}")
async def frontend_update_task(
    task_id: str,
    data: FrontendTaskUpdate,
    current_user: User = Depends(get_current_user),
):
    svc = TaskService()
    try:
        status_value = TaskStatus[data.status] if data.status else None
        priority_value = TaskPriority[data.priority] if data.priority else None
    except KeyError as exc:
        raise bad_request(f"Unsupported enum value: {exc.args[0]}")
    payload = TaskUpdate(
        title=data.title,
        description=data.description,
        assignee_id=(data.assignee_ids[0] if data.assignee_ids else None) if data.assignee_ids is not None else None,
        owner_id=data.owner_id,
        due_date=data.deadline,
        status=status_value,
        priority=priority_value,
    )
    task = await svc.update(task_id, payload, current_user.id)
    return _task_to_frontend(task)


@router.get("/tasks/{task_id}")
async def frontend_get_task(task_id: str, current_user: User = Depends(get_current_user)):
    svc = TaskService()
    task = await svc.get_or_404(task_id)
    await svc.project_svc._require_project_member(task.project_id, current_user.id)
    return _task_to_frontend(task)


@router.delete("/tasks/{task_id}", status_code=204)
async def frontend_delete_task(task_id: str, current_user: User = Depends(get_current_user)):
    svc = TaskService()
    await svc.delete(task_id, current_user.id)


@router.post("/transcripts")
async def frontend_create_transcript(data: FrontendTranscriptCreate, current_user: User = Depends(get_current_user)):
    meeting_svc = MeetingService()

    if data.meeting_id:
        meeting_id = data.meeting_id
    else:
        meeting = await meeting_svc.create(
            MeetingCreate(project_id=data.project_id, title=data.meeting_title),
            current_user.id,
        )
        meeting_id = str(meeting.id)

    transcript = await meeting_svc.upload_transcript(
        meeting_id,
        data.transcript_text,
        f"api_{datetime.utcnow().timestamp()}.txt",
        current_user.id,
    )
    return _transcript_to_frontend(transcript)


@router.get("/transcripts")
async def frontend_list_transcripts(
    projectId: str = Query(...),
    current_user: User = Depends(get_current_user),
):
    project_svc = ProjectService()
    await project_svc._require_project_member(projectId, current_user.id)
    meetings = await MeetingRepository.list_for_project(PydanticObjectId(projectId), 0, 5000)
    meeting_ids = [m.id for m in meetings]
    if not meeting_ids:
        return []
    transcripts = await Transcript.find({"meeting_id": {"$in": meeting_ids}}).sort("-created_at").to_list()
    return [_transcript_to_frontend(t) for t in transcripts]


@router.get("/transcripts/{transcript_id}")
async def frontend_get_transcript(transcript_id: str, current_user: User = Depends(get_current_user)):
    svc = MeetingService()
    transcript = await svc.get_transcript_by_id(transcript_id, current_user.id)
    return _transcript_to_frontend(transcript)


@router.post("/processing/start")
async def frontend_start_processing(data: FrontendStartProcessingRequest, current_user: User = Depends(get_current_user)):
    svc = ProcessingService()
    job = await svc.start_job(data.transcript_id, data.project_id, current_user.id)
    return {"jobId": str(job.id)}


@router.get("/processing/{job_id}/status")
async def frontend_processing_status(job_id: str, current_user: User = Depends(get_current_user)):
    svc = ProcessingService()
    job = await svc.get_job(job_id, current_user.id)
    progress = int((job.current_step / JOB_TOTAL_STEPS) * 100) if JOB_TOTAL_STEPS else 0
    return {
        "jobId": str(job.id),
        "status": job.status.value,
        "currentStep": job.current_step,
        "stepLabel": job.step_label,
        "summary": job.summary,
        "actionItemIds": [str(i) for i in job.action_item_ids],
        "progress": progress,
    }


@router.post("/processing/{job_id}/cancel")
async def frontend_cancel_processing(job_id: str, current_user: User = Depends(get_current_user)):
    svc = ProcessingService()
    job = await svc.cancel_job(job_id, current_user.id)
    progress = int((job.current_step / JOB_TOTAL_STEPS) * 100) if JOB_TOTAL_STEPS else 0
    return {
        "jobId": str(job.id),
        "status": job.status.value,
        "currentStep": job.current_step,
        "stepLabel": job.step_label,
        "summary": job.summary,
        "actionItemIds": [str(i) for i in job.action_item_ids],
        "progress": progress,
    }


@router.post("/processing/{job_id}/retry")
async def frontend_retry_processing(job_id: str, current_user: User = Depends(get_current_user)):
    svc = ProcessingService()
    new_job = await svc.retry_job(job_id, current_user.id)
    return {"jobId": str(new_job.id)}


@router.delete("/meetings/{meeting_id}", status_code=204)
async def frontend_delete_meeting(meeting_id: str, current_user: User = Depends(get_current_user)):
    svc = MeetingService()
    await svc.delete(meeting_id, current_user.id)


@router.delete("/transcripts/{transcript_id}", status_code=204)
async def frontend_delete_transcript(transcript_id: str, current_user: User = Depends(get_current_user)):
    svc = MeetingService()
    await svc.delete_transcript(transcript_id, current_user.id)


@router.post("/publish")
async def frontend_publish(data: FrontendPublishRequest, current_user: User = Depends(get_current_user)):
    project_svc = ProjectService()
    project = await project_svc._require_project_member(data.project_id, current_user.id)

    transcript = None
    meeting = None
    if data.transcript_id:
        transcript = await TranscriptRepository.get_by_id(data.transcript_id)
        if transcript:
            meeting = await MeetingRepository.get_by_id(str(transcript.meeting_id))

    if meeting and data.summary is not None:
        await MeetingSummaryRepository.upsert(
            meeting,
            summary_text=data.summary,
            key_points=[],
            decisions=[],
            raw_nlp_output={"source": "publish_api"},
        )

    task_svc = TaskService()
    created_ids: list[str] = []
    for item in data.action_items:
        created_task = await task_svc.create_manual(
            TaskCreate(
                project_id=data.project_id,
                title=item.title,
                description=item.description,
                assignee_id=item.assignee_ids[0] if item.assignee_ids else None,
                owner_id=item.owner_id,
                due_date=item.deadline,
            ),
            current_user.id,
        )
        if transcript and item.quote:
            created_task.evidence.append(
                TaskEvidence(
                    transcript_id=transcript.id,
                    speaker=item.speaker,
                    transcript_timestamp=item.timestamp,
                    quote=item.quote,
                )
            )
            await created_task.save()
        created_ids.append(str(created_task.id))

    note_svc = NotificationService()
    await note_svc.create_for_project(
        str(project.id),
        f"Transcript published to project {project.name}",
        NotificationType.SUCCESS,
    )

    recipients = {str(project.owner_id), str(project.created_by)}
    recipients.update(str(member.user_id) for member in project.members)
    await realtime_hub.emit_to_users(
        list(recipients),
        "publish",
        {
            "projectId": str(project.id),
            "transcriptId": data.transcript_id,
            "taskIds": created_ids,
            "summary": data.summary,
        },
    )

    return {"success": True, "taskIds": created_ids}


@router.get("/notifications")
async def frontend_notifications(current_user: User = Depends(get_current_user)):
    svc = NotificationService()
    notes = await svc.list_for_user(current_user.id)
    return [_notification_to_frontend(n) for n in notes]


@router.post("/notifications/read")
async def frontend_notifications_read(
    data: NotificationsReadRequest = Body(default=NotificationsReadRequest()),
    current_user: User = Depends(get_current_user),
):
    svc = NotificationService()
    updated = await svc.mark_read(current_user.id, data.ids)
    return {"updated": updated}


@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    token = websocket.query_params.get("token")
    if not token:
        logger.error("WS REJECTED: Missing token")
        await websocket.close(code=1008)
        return

    try:
        payload = decode_token(token)
    except Exception as e:
        logger.error(f"WS REJECTED: Decode error {e}")
        await websocket.close(code=1008)
        return

    if payload.get("type") != "access":
        logger.error("WS REJECTED: Invalid token type")
        await websocket.close(code=1008)
        return

    user_id = payload.get("sub")
    if not user_id:
        logger.error("WS REJECTED: No user_id in payload")
        await websocket.close(code=1008)
        return

    try:
        user = await UserRepository.get_by_id(user_id)
    except Exception as e:
        logger.error(f"WS REJECTED: DB error {e}")
        await websocket.close(code=1008)
        return

    if not user:
        logger.error("WS REJECTED: User not found in DB")
        await websocket.close(code=1008)
        return
    if not user.is_active:
        logger.error("WS REJECTED: User inactive")
        await websocket.close(code=1008)
        return

    try:
        await realtime_hub.connect(str(user.id), websocket)
        logger.info(f"WS ACCEPTED for user {user.id}")
    except Exception as e:
        logger.error(f"WS ACCEPTED AND THEN CRASHED in hub: {e}")
        return

    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        realtime_hub.disconnect(str(user.id), websocket)

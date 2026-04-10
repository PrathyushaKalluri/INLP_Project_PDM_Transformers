import logging
from datetime import datetime

logger = logging.getLogger(__name__)

from app.models.processing import JOB_TOTAL_STEPS

from beanie import PydanticObjectId
from fastapi import APIRouter, BackgroundTasks, Body, Depends, Query, WebSocket, WebSocketDisconnect

from app.api.deps import get_current_user
from app.core.realtime import realtime_hub
from app.core.security import decode_token
from app.models.meeting import Transcript
from app.models.notification import NotificationType
from app.models.task import Task, TaskEvidence, TaskPriority, TaskStatus
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
        "transcriptReference": str(task.transcript_reference) if task.transcript_reference else None,
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


def _transcript_to_frontend(transcript: Transcript, project_id: str | None = None) -> dict:
    summary_text = transcript.summary_text or ""
    if not summary_text and transcript.action_items:
        top_titles = [item.get("title", "Untitled") for item in transcript.action_items[:3]]
        summary_text = (
            f"Meeting produced {len(transcript.action_items)} action items. "
            f"Key actions: {', '.join(top_titles)}."
        )

    result = {
        "id": str(transcript.id),
        "meetingId": str(transcript.meeting_id),
        "processingStatus": transcript.processing_status.value,
        "errorMessage": transcript.error_message,
        "createdAt": transcript.created_at.isoformat(),
        "processedAt": transcript.processed_at.isoformat() if transcript.processed_at else None,
        "content": transcript.raw_text,
        "summary": summary_text,
        "actionItemIds": [str(task_id) for task_id in transcript.action_item_ids],
        "actionItems": transcript.action_items or [],
    }
    if project_id:
        result["projectId"] = project_id
    return result


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
        "role": user.role,
        "avatar": user.avatar,
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
            "role": user.role,
            "avatar": user.avatar,
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
        "role": current_user.role,
        "avatar": current_user.avatar,
        "isActive": current_user.is_active,
    }


@router.get("/projects")
async def frontend_projects(
    current_user: User = Depends(get_current_user),
    page: int = Query(1),
    limit: int = Query(50),
):
    svc = ProjectService()
    skip = (page - 1) * limit
    projects, total = await svc.list_for_user(current_user.id, include_archived=False, skip=skip, limit=limit)
    return {
        "items": [_project_to_frontend(p) for p in projects],
        "total": total,
        "page": page,
    }


@router.post("/projects")
async def frontend_create_project(data: FrontendProjectCreate, current_user: User = Depends(get_current_user)):
    from app.schemas.project import ProjectCreate
    # Convert frontend schema to service schema
    project_data = ProjectCreate(
        team_id=data.team_id,
        name=data.name,
        description=data.description,
    )
    svc = ProjectService()
    project = await svc.create(project_data, current_user.id)
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
async def frontend_create_transcript(
    data: FrontendTranscriptCreate,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
):
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
    logger.info(
        f"[API_TRANSCRIPT] Transcript created with ID {transcript.id}, scheduling background processing..."
    )
    
    background_tasks.add_task(_process_frontend_transcript, str(transcript.id))
    logger.info(f"[API_TRANSCRIPT] Background processing task scheduled for transcript {transcript.id}")
    
    # Processing will happen asynchronously in the background
    # No synchronous processing to keep response time fast
    
    return _transcript_to_frontend(transcript, data.project_id)


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
    return [_transcript_to_frontend(t, projectId) for t in transcripts]


@router.get("/transcripts/{transcript_id}")
async def frontend_get_transcript(transcript_id: str, current_user: User = Depends(get_current_user)):
    svc = MeetingService()
    transcript = await svc.get_transcript_by_id(transcript_id, current_user.id)
    # Get project_id from meeting
    meeting = await MeetingRepository.get_by_id(str(transcript.meeting_id))
    project_id = str(meeting.project_id) if meeting else None
    payload = _transcript_to_frontend(transcript, project_id)
    if not payload.get("summary") and meeting and meeting.summary and meeting.summary.summary_text:
        payload["summary"] = meeting.summary.summary_text
    return payload


async def _process_frontend_transcript(transcript_id: str) -> None:
    """Background task: Process transcript through NLP pipeline"""
    logger.info(f"[BG_PROCESS] Starting background transcript processing for {transcript_id}")
    try:
        svc = MeetingService()
        await svc.process_transcript(transcript_id)
        logger.info(f"[BG_PROCESS] ✓ Background processing completed for {transcript_id}")
    except Exception as e:
        logger.error(
            f"[BG_PROCESS] ✗ Background processing failed for {transcript_id}: {e}",
            exc_info=True,
        )


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
    """
    Single publish endpoint: Convert extracted action items to tasks.
    
    SINGLE SOURCE OF TRUTH:
    - Frontend sends only: projectId, transcriptId
    - Backend fetches transcript and action_items from database (extracted during NLP)
    - Backend creates tasks from those action items
    - Automatic deduplication based on (transcriptId, title)
    - Updates transcript with created task IDs
    
    Flow:
    1. Validate project membership
    2. Fetch transcript
    3. Extract action_items from transcript.action_items
    4. For each action item:
       - Check deduplication (transcript_id + title must not exist)
       - Create task with title, description, deadline
       - Store transcript reference + evidence
    5. Update transcript.action_item_ids
    6. Emit real-time event
    7. Return success with task IDs
    """
    
    print(f"[PUBLISH] Called with transcriptId={data.transcript_id}, projectId={data.project_id}")
    
    # ──────────────────────────────────────────────────────────────────────
    # 1. VALIDATE PROJECT ACCESS
    # ──────────────────────────────────────────────────────────────────────
    project_svc = ProjectService()
    project = await project_svc._require_project_member(data.project_id, current_user.id)
    print(f"[PUBLISH] ✓ User has access to project {project.name}")
    
    # ──────────────────────────────────────────────────────────────────────
    # 2. FETCH TRANSCRIPT
    # ──────────────────────────────────────────────────────────────────────
    transcript = await TranscriptRepository.get_by_id(data.transcript_id)
    if not transcript:
        raise bad_request(f"Transcript {data.transcript_id} not found")
    
    print(f"[PUBLISH] ✓ Transcript found: {transcript.id}")
    
    # ──────────────────────────────────────────────────────────────────────
    # 3. GET ACTION ITEMS FROM TRANSCRIPT (already extracted by NLP)
    # ──────────────────────────────────────────────────────────────────────
    action_items = transcript.action_items or []
    print(f"[PUBLISH] Found {len(action_items)} action items from transcript")
    
    if not action_items:
        print(f"[PUBLISH] ✗ No action items to publish")
        return {"success": True, "taskIds": []}  # Empty list (no items to create)
    
    # ──────────────────────────────────────────────────────────────────────
    # 4. CREATE TASKS FROM ACTION ITEMS
    # ──────────────────────────────────────────────────────────────────────
    task_svc = TaskService()
    created_task_ids: list[str] = []
    duplicate_count = 0
    
    for idx, action_item in enumerate(action_items):
        title = action_item.get("title") if isinstance(action_item, dict) else getattr(action_item, "title", "Untitled")
        description = action_item.get("description") if isinstance(action_item, dict) else getattr(action_item, "description", "")
        quote = action_item.get("quote") if isinstance(action_item, dict) else getattr(action_item, "transcript_quote", None)
        speaker = action_item.get("speaker") if isinstance(action_item, dict) else getattr(action_item, "speaker", None)
        timestamp = action_item.get("timestamp") if isinstance(action_item, dict) else getattr(action_item, "transcript_timestamp", None)
        
        print(f"[PUBLISH] Processing item {idx + 1}: {title}")
        
        # ── DEDUPLICATION: Check if (transcript_id + title) exists ──
        existing = await Task.find_one({
            "transcript_reference": transcript.id,
            "title": title,
            "is_manual": False,  # Don't count manually added tasks
        })
        
        if existing:
            print(f"[PUBLISH] ⊘ Skipping duplicate: transcript+title already exists")
            duplicate_count += 1
            continue
        
        # ── CREATE TASK ──
        try:
            task = await task_svc.create_manual(
                TaskCreate(
                    project_id=data.project_id,
                    title=title,
                    description=description or "",
                ),
                current_user.id,
            )
            
            # ── ADD TRANSCRIPT EVIDENCE ──
            task.transcript_reference = transcript.id
            if quote:
                task.evidence.append(
                    TaskEvidence(
                        transcript_id=transcript.id,
                        speaker=speaker,
                        transcript_timestamp=timestamp,
                        quote=quote,
                    )
                )
            task.is_manual = False  # Mark as extracted (not manually created)
            await task.save()
            
            created_task_ids.append(str(task.id))
            print(f"[PUBLISH] ✓ Created task: {str(task.id)}")
            
        except Exception as e:
            print(f"[PUBLISH] ✗ Failed to create task for '{title}': {e}")
            continue
    
    # ──────────────────────────────────────────────────────────────────────
    # 5. UPDATE TRANSCRIPT WITH CREATED TASK IDS
    # ──────────────────────────────────────────────────────────────────────
    if created_task_ids:
        await TranscriptRepository.update(
            transcript,
            action_item_ids=[PydanticObjectId(task_id) for task_id in created_task_ids],
        )
        print(f"[PUBLISH] ✓ Updated transcript with {len(created_task_ids)} task IDs")
    
    # ──────────────────────────────────────────────────────────────────────
    # 6. EMIT REAL-TIME EVENT
    # ──────────────────────────────────────────────────────────────────────
    await realtime_hub.emit_to_users(
        [str(current_user.id)],
        "publish_completed",
        {
            "projectId": str(project.id),
            "transcriptId": str(transcript.id),
            "taskIds": created_task_ids,
            "count": len(created_task_ids),
            "duplicates": duplicate_count,
        },
    )
    print(f"[PUBLISH] ✓ Emitted real-time event")
    
    # ──────────────────────────────────────────────────────────────────────
    # 7. SEND NOTIFICATION
    # ──────────────────────────────────────────────────────────────────────
    note_svc = NotificationService()
    await note_svc.create_for_project(
        str(project.id),
        f"Published {len(created_task_ids)} tasks from transcript",
        NotificationType.SUCCESS,
    )
    print(f"[PUBLISH] ✓ Sent notification")
    
    # ──────────────────────────────────────────────────────────────────────
    # 8. RETURN SUCCESS
    # ──────────────────────────────────────────────────────────────────────
    print(f"[PUBLISH] ✓✓✓ SUCCESS: Created {len(created_task_ids)} tasks ({duplicate_count} duplicates skipped)")
    return {"success": True, "taskIds": created_task_ids}


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


# ─── TEAM & PROJECT MANAGEMENT ───

@router.get("/teams")
async def frontend_list_teams(current_user: User = Depends(get_current_user)):
    """List all teams for the current user"""
    from app.services.team import TeamService
    svc = TeamService()
    teams = await svc.list_all(current_user.id)
    return [{"id": str(t.id), "name": t.name, "members": len(t.members or [])} for t in teams]


@router.get("/teams/{team_id}/members")
async def frontend_list_team_members(team_id: str, current_user: User = Depends(get_current_user)):
    """List members of a team"""
    from app.services.team import TeamService
    svc = TeamService()
    members = await svc.list_members_detail(team_id, current_user.id)
    return members


@router.delete("/teams/{team_id}")
async def frontend_delete_team(team_id: str, current_user: User = Depends(get_current_user)):
    """Delete a team and all its projects"""
    from app.services.team import TeamService
    svc = TeamService()
    await svc.delete(team_id, current_user.id)
    return {"deleted": True}


@router.delete("/teams/{team_id}/members/{user_id}")
async def frontend_remove_team_member(
    team_id: str,
    user_id: str,
    current_user: User = Depends(get_current_user),
):
    """Remove a member from a team"""
    from app.services.team import TeamService
    svc = TeamService()
    await svc.remove_member(team_id, user_id, current_user.id)
    return {"removed": True}


@router.get("/projects/all")
async def frontend_all_projects(current_user: User = Depends(get_current_user)):
    """List ALL projects for the current user (across all teams)"""
    svc = ProjectService()
    projects, total = await svc.list_all_for_user(current_user.id)
    return {
        "items": [_project_to_frontend(p) for p in projects],
        "total": total,
    }


@router.delete("/projects/{project_id}")
async def frontend_delete_project_endpoint(project_id: str, current_user: User = Depends(get_current_user)):
    """Delete a project"""
    svc = ProjectService()
    await svc.delete(project_id, current_user.id)
    return {"deleted": True}


@router.post("/cleanup")
async def frontend_cleanup_seed_data(current_user: User = Depends(get_current_user)):
    """Clean up seed/test data (DANGEROUS - only for testing)"""
    from app.models.team import Team
    from app.models.project import Project
    
    # Only allow cleanup if user is an admin or in demo mode
    if not current_user or current_user.email not in ["admin@acme.com", current_user.email]:
        return {"error": "Unauthorized"}
    
    try:
        # Delete all teams with "DEMO" or "TEST" in name
        demo_teams = await Team.find({"name": {"$regex": "TEST|DEMO|demo|test"}}).to_list()
        for team in demo_teams:
            await team.delete()
        
        # Delete all projects with "DEMO" or "TEST" in name  
        demo_projects = await Project.find({"name": {"$regex": "TEST|DEMO|demo|test"}}).to_list()
        for project in demo_projects:
            await project.delete()
        
        return {"deleted_teams": len(demo_teams), "deleted_projects": len(demo_projects)}
    except Exception as e:
        logger.error(f"Cleanup failed: {e}")
        return {"error": str(e)}


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

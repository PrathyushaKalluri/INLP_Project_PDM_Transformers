from datetime import datetime, timezone

from beanie import PydanticObjectId

from app.models.task import (
    SuggestionReviewStatus, SubTask, Task, TaskEvidence, TaskNote,
    TaskStatus, TaskStatusHistory, TaskSuggestion,
)
from app.repositories.user import UserRepository
from app.repositories.task import TaskRepository, TaskSuggestionRepository
from app.schemas.task import (
    SuggestionApproveRequest, SuggestionReviewUpdate,
    SubTaskCreate, SubTaskUpdate, TaskCreate, TaskNoteCreate, TaskUpdate,
)
from app.services.errors import bad_request, conflict, forbidden, not_found
from app.services.notification import NotificationService
from app.services.project import ProjectService
from app.models.task import TaskPriority
from app.models.notification import NotificationType
from app.core.realtime import realtime_hub


class TaskService:
    def __init__(self) -> None:
        self.project_svc = ProjectService()
        self.notification_svc = NotificationService()

    # ── Task CRUD ──────────────────────────────────────────────────────────────

    async def create_manual(self, data: TaskCreate, creator_id: PydanticObjectId) -> Task:
        project = await self.project_svc.get_or_404(data.project_id)
        await self.project_svc._require_project_member(project.id, creator_id)
        owner_id = PydanticObjectId(data.owner_id) if data.owner_id else getattr(project, "owner_id", project.created_by)
        task = Task(
            project_id=project.id,
            team_id=project.team_id,
            title=data.title,
            description=data.description,
            status=data.status,
            priority=data.priority,
            assignee_id=PydanticObjectId(data.assignee_id) if data.assignee_id else None,
            owner_id=owner_id,
            due_date=data.due_date,
            created_by=creator_id,
            is_manual=True,
            status_history=[TaskStatusHistory(old_status=None, new_status=data.status.value, changed_by=creator_id)],
        )
        await task.insert()
        await self.notification_svc.create_for_project(
            str(project.id),
            f"Task created: {task.title}",
            NotificationType.SUCCESS,
        )
        await self._emit_project_task_event(str(project.id), "task_created", task)
        return task

    async def get_or_404(self, task_id: str) -> Task:
        task = await TaskRepository.get_by_id(task_id)
        if not task:
            raise not_found("Task")
        return task

    async def update(self, task_id: str, data: TaskUpdate, requester_id: PydanticObjectId) -> Task:
        task = await self.get_or_404(task_id)
        await self.project_svc._require_project_member(task.project_id, requester_id)

        await self._require_manager_role(requester_id)

        old_status = task.status
        updates = {k: v for k, v in data.model_dump().items() if v is not None}
        if "assignee_id" in updates and updates["assignee_id"]:
            updates["assignee_id"] = PydanticObjectId(updates["assignee_id"])
        if "owner_id" in updates and updates["owner_id"]:
            updates["owner_id"] = PydanticObjectId(updates["owner_id"])
        await TaskRepository.update(task, **updates)

        if data.status and data.status != old_status:
            await self._record_status_change(task, old_status.value, data.status.value, requester_id)
        await self.notification_svc.create_for_project(
            str(task.project_id),
            f"Task updated: {task.title}",
            NotificationType.INFO,
        )
        await self._emit_project_task_event(str(task.project_id), "task_updated", task)
        return task

    async def _require_manager_role(self, requester_id: PydanticObjectId) -> None:
        user = await UserRepository.get_by_id(str(requester_id))
        if not user or str(getattr(user, "role", "")).lower() != "manager":
            raise forbidden("Only managers can edit tasks.")

    async def delete(self, task_id: str, requester_id: PydanticObjectId) -> None:
        task = await self.get_or_404(task_id)
        await self.project_svc._require_project_member(task.project_id, requester_id)
        self._require_task_owner(task, requester_id)
        await self.notification_svc.create_for_project(
            str(task.project_id),
            f"Task deleted: {task.title}",
            NotificationType.WARNING,
        )
        await self._emit_project_task_event(str(task.project_id), "task_deleted", {"taskId": str(task.id)})
        await task.delete()

    async def list_filtered(self, requester_id: PydanticObjectId, **filters) -> tuple[list[Task], int]:
        team_id = filters.get("team_id")
        project_id = filters.get("project_id")
        if project_id:
            await self.project_svc._require_project_member(project_id, requester_id)
        elif team_id:
            from app.services.team import TeamService
            team_svc = TeamService()
            if not await team_svc.is_member(team_id, requester_id):
                raise forbidden("You are not a member of this team.")
        else:
            accessible_project_ids = await self.project_svc.list_ids_for_user(requester_id)
            filters["project_ids"] = [str(pid) for pid in accessible_project_ids]

        skip = filters.pop("skip", 0)
        limit = filters.pop("limit", 50)
        sort_by = filters.pop("sort_by", "created_at")
        sort_order = filters.pop("sort_order", "desc")

        tasks = await TaskRepository.list_filtered(skip=skip, limit=limit, sort_by=sort_by, sort_order=sort_order, **filters)
        total = await TaskRepository.count_filtered(**filters)
        return tasks, total

    # ── Task Suggestion Review ─────────────────────────────────────────────────

    async def get_suggestions_for_meeting(
        self, meeting_id: str, requester_id: PydanticObjectId, status: SuggestionReviewStatus | None = None
    ) -> list[TaskSuggestion]:
        from app.services.meeting import MeetingService
        meeting = await MeetingService().get_or_404(meeting_id)
        await self.project_svc._require_project_member(meeting.project_id, requester_id)
        return await TaskSuggestionRepository.list_for_meeting(meeting.id, status)

    async def update_suggestion(
        self, suggestion_id: str, data: SuggestionReviewUpdate, requester_id: PydanticObjectId
    ) -> TaskSuggestion:
        suggestion = await self._get_suggestion_or_404(suggestion_id)
        await self._require_suggestion_access(suggestion, requester_id)
        was_pending = suggestion.review_status == SuggestionReviewStatus.PENDING
        updates = data.model_dump(exclude_none=True)
        if was_pending and "review_status" not in updates:
            updates["review_status"] = SuggestionReviewStatus.MODIFIED
        await TaskSuggestionRepository.update(suggestion, **updates)
        return suggestion

    async def approve_suggestion(
        self, suggestion_id: str, data: SuggestionApproveRequest, requester_id: PydanticObjectId
    ) -> Task:
        suggestion = await self._get_suggestion_or_404(suggestion_id)
        await self._require_suggestion_access(suggestion, requester_id)
        if suggestion.review_status == SuggestionReviewStatus.REJECTED:
            raise bad_request("Cannot approve a rejected suggestion.")
        if suggestion.task_id:
            raise conflict("Suggestion has already been approved.")

        from app.services.meeting import MeetingService
        meeting = await MeetingService().get_or_404(str(suggestion.meeting_id))

        initial_evidence = []
        if suggestion.transcript_quote:
            initial_evidence.append(TaskEvidence(
                transcript_id=suggestion.transcript_id,
                speaker=suggestion.speaker,
                transcript_timestamp=suggestion.transcript_timestamp,
                quote=suggestion.transcript_quote,
            ))

        task = Task(
            project_id=meeting.project_id,
            team_id=meeting.team_id,
            meeting_id=suggestion.meeting_id,
            task_suggestion_id=suggestion.id,
            transcript_reference=suggestion.transcript_id,
            title=data.title or suggestion.suggested_title,
            description=data.description or suggestion.suggested_description,
            status=data.status,
            priority=data.priority,
            assignee_id=PydanticObjectId(data.assignee_id) if data.assignee_id else None,
            owner_id=PydanticObjectId(data.owner_id) if data.owner_id else requester_id,
            due_date=data.due_date or suggestion.suggested_deadline,
            created_by=requester_id,
            is_manual=False,
            evidence=initial_evidence,
            status_history=[TaskStatusHistory(old_status=None, new_status=data.status.value, changed_by=requester_id)],
        )
        await task.insert()

        await TaskSuggestionRepository.update(
            suggestion,
            review_status=SuggestionReviewStatus.APPROVED,
            reviewed_by=requester_id,
            task_id=task.id,
        )
        await self.notification_svc.create_for_project(
            str(meeting.project_id),
            f"Suggestion approved and task created: {task.title}",
            NotificationType.SUCCESS,
        )
        await self._emit_project_task_event(str(meeting.project_id), "task_created", task)
        return task

    async def reject_suggestion(self, suggestion_id: str, requester_id: PydanticObjectId) -> TaskSuggestion:
        suggestion = await self._get_suggestion_or_404(suggestion_id)
        await self._require_suggestion_access(suggestion, requester_id)
        await TaskSuggestionRepository.update(
            suggestion,
            review_status=SuggestionReviewStatus.REJECTED,
            reviewed_by=requester_id,
        )
        return suggestion

    # ── Evidence ───────────────────────────────────────────────────────────────

    async def get_evidence(self, task_id: str, requester_id: PydanticObjectId) -> list[TaskEvidence]:
        task = await self.get_or_404(task_id)
        await self.project_svc._require_project_member(task.project_id, requester_id)
        return task.evidence

    # ── SubTasks ───────────────────────────────────────────────────────────────

    async def get_subtasks(self, task_id: str, requester_id: PydanticObjectId) -> list[SubTask]:
        task = await self.get_or_404(task_id)
        await self.project_svc._require_project_member(task.project_id, requester_id)
        return task.subtasks

    async def create_subtask(
        self, task_id: str, data: SubTaskCreate, creator_id: PydanticObjectId
    ) -> SubTask:
        task = await self.get_or_404(task_id)
        await self.project_svc._require_project_member(task.project_id, creator_id)
        subtask = SubTask(
            title=data.title,
            description=data.description,
            assignee_id=PydanticObjectId(data.assignee_id) if data.assignee_id else None,
            created_by=creator_id,
        )
        task.subtasks.append(subtask)
        await task.save()
        return subtask

    async def update_subtask(
        self, task_id: str, subtask_id: str, data: SubTaskUpdate, requester_id: PydanticObjectId
    ) -> SubTask:
        task = await self.get_or_404(task_id)
        await self.project_svc._require_project_member(task.project_id, requester_id)
        try:
            subtask_oid = PydanticObjectId(subtask_id)
        except Exception:
            raise not_found("Subtask")
        subtask = next((s for s in task.subtasks if s.id == subtask_oid), None)
        if not subtask:
            raise not_found("Subtask")
        for k, v in data.model_dump(exclude_none=True).items():
            setattr(subtask, k, v)
        subtask.updated_at = datetime.now(timezone.utc)
        await task.save()
        return subtask

    # ── Notes ──────────────────────────────────────────────────────────────────

    async def get_notes(self, task_id: str, requester_id: PydanticObjectId) -> list[TaskNote]:
        task = await self.get_or_404(task_id)
        await self.project_svc._require_project_member(task.project_id, requester_id)
        return task.notes

    async def create_note(
        self, task_id: str, data: TaskNoteCreate, creator_id: PydanticObjectId
    ) -> TaskNote:
        task = await self.get_or_404(task_id)
        await self.project_svc._require_project_member(task.project_id, creator_id)
        note = TaskNote(content=data.content, created_by=creator_id)
        task.notes.append(note)
        await task.save()
        return note

    # ── Status History ─────────────────────────────────────────────────────────

    async def get_status_history(self, task_id: str, requester_id: PydanticObjectId) -> list[TaskStatusHistory]:
        task = await self.get_or_404(task_id)
        await self.project_svc._require_project_member(task.project_id, requester_id)
        return task.status_history

    # ── Helpers ────────────────────────────────────────────────────────────────

    async def _record_status_change(
        self,
        task: Task,
        old_status: str | None,
        new_status: str,
        changed_by: PydanticObjectId,
    ) -> None:
        task.status_history.append(TaskStatusHistory(
            old_status=old_status,
            new_status=new_status,
            changed_by=changed_by,
        ))
        await task.save()

    async def _get_suggestion_or_404(self, suggestion_id: str) -> TaskSuggestion:
        suggestion = await TaskSuggestionRepository.get_by_id(suggestion_id)
        if not suggestion:
            raise not_found("Task suggestion")
        return suggestion

    async def _require_suggestion_access(self, suggestion: TaskSuggestion, requester_id: PydanticObjectId) -> None:
        from app.services.meeting import MeetingService
        meeting = await MeetingService().get_or_404(str(suggestion.meeting_id))
        await self.project_svc._require_project_member(meeting.project_id, requester_id)

    def _require_task_owner(self, task: Task, requester_id: PydanticObjectId) -> None:
        if task.owner_id is None:
            # Allow any project member to edit/delete tasks with no owner.
            # Project membership is already verified by the caller.
            return
        if task.owner_id != requester_id:
            raise forbidden("Only task owner can edit or delete this task.")

    async def _emit_project_task_event(self, project_id: str, event_type: str, task_or_payload) -> None:
        project = await self.project_svc.get_or_404(project_id)
        user_ids: set[str] = {str(project.owner_id), str(project.created_by)}
        user_ids.update(str(member.user_id) for member in project.members)

        if isinstance(task_or_payload, dict):
            payload = task_or_payload
        else:
            payload = {
                "id": str(task_or_payload.id),
                "projectId": str(task_or_payload.project_id),
                "title": task_or_payload.title,
                "status": task_or_payload.status.value,
                "priority": task_or_payload.priority.value,
            }
        await realtime_hub.emit_to_users(list(user_ids), event_type, payload)

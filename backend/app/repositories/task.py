from datetime import date, datetime, timezone
from typing import Any

from beanie import PydanticObjectId

from app.models.task import (
    Task,
    TaskSuggestion,
    TaskStatus,
    TaskPriority,
    SuggestionReviewStatus,
)


class TaskRepository:
    @staticmethod
    async def get_by_id(id: str) -> Task | None:
        try:
            return await Task.get(PydanticObjectId(id))
        except Exception:
            return None

    @staticmethod
    async def list_filtered(
        project_id: str | None = None,
        team_id: str | None = None,
        meeting_id: str | None = None,
        assignee_id: str | None = None,
        owner_id: str | None = None,
        status: TaskStatus | None = None,
        priority: TaskPriority | None = None,
        due_before: date | None = None,
        due_after: date | None = None,
        is_manual: bool | None = None,
        skip: int = 0,
        limit: int = 50,
        sort_by: str = "created_at",
        sort_order: str = "desc",
    ) -> list[Task]:
        filters: dict[str, Any] = {}
        if project_id:
            filters["project_id"] = PydanticObjectId(project_id)
        if team_id:
            filters["team_id"] = PydanticObjectId(team_id)
        if meeting_id:
            filters["meeting_id"] = PydanticObjectId(meeting_id)
        if assignee_id:
            filters["assignee_id"] = PydanticObjectId(assignee_id)
        if owner_id:
            filters["owner_id"] = PydanticObjectId(owner_id)
        if status:
            filters["status"] = status
        if priority:
            filters["priority"] = priority
        if due_before:
            filters["due_date"] = {"$lte": due_before.isoformat()}
        if due_after:
            filters.setdefault("due_date", {})["$gte"] = due_after.isoformat()
        if is_manual is not None:
            filters["is_manual"] = is_manual

        sort_prefix = "-" if sort_order == "desc" else "+"
        sort_field = f"{sort_prefix}{sort_by}"
        return (
            await Task.find(filters)
            .sort(sort_field)
            .skip(skip)
            .limit(limit)
            .to_list()
        )

    @staticmethod
    async def count_filtered(**kwargs) -> int:
        filters: dict[str, Any] = {}
        for key in ("project_id", "team_id", "meeting_id", "assignee_id", "owner_id"):
            if kwargs.get(key):
                filters[key] = PydanticObjectId(kwargs[key])
        for key in ("status", "priority", "is_manual"):
            if kwargs.get(key) is not None:
                filters[key] = kwargs[key]
        return await Task.find(filters).count()

    @staticmethod
    async def create(**kwargs) -> Task:
        task = Task(**kwargs)
        await task.insert()
        return task

    @staticmethod
    async def update(task: Task, **kwargs) -> Task:
        for k, v in kwargs.items():
            setattr(task, k, v)
        task.updated_at = datetime.now(timezone.utc)
        await task.save()
        return task


class TaskSuggestionRepository:
    @staticmethod
    async def get_by_id(id: str) -> TaskSuggestion | None:
        try:
            return await TaskSuggestion.get(PydanticObjectId(id))
        except Exception:
            return None

    @staticmethod
    async def list_for_meeting(
        meeting_id: PydanticObjectId,
        review_status: SuggestionReviewStatus | None = None,
    ) -> list[TaskSuggestion]:
        query = TaskSuggestion.find(TaskSuggestion.meeting_id == meeting_id)
        if review_status:
            query = query.find(TaskSuggestion.review_status == review_status)
        return await query.to_list()

    @staticmethod
    async def create(**kwargs) -> TaskSuggestion:
        suggestion = TaskSuggestion(**kwargs)
        await suggestion.insert()
        return suggestion

    @staticmethod
    async def update(suggestion: TaskSuggestion, **kwargs) -> TaskSuggestion:
        for k, v in kwargs.items():
            setattr(suggestion, k, v)
        suggestion.updated_at = datetime.now(timezone.utc)
        await suggestion.save()
        return suggestion

from beanie import PydanticObjectId

from app.core.realtime import realtime_hub
from app.models.notification import Notification, NotificationType
from app.services.project import ProjectService


class NotificationService:
    def __init__(self) -> None:
        self.project_svc = ProjectService()

    async def list_for_user(self, user_id: PydanticObjectId) -> list[Notification]:
        return await Notification.find(Notification.user_id == user_id).sort("-created_at").to_list()

    async def mark_read(self, user_id: PydanticObjectId, ids: list[str] | None = None) -> int:
        if ids:
            oid_list = [PydanticObjectId(i) for i in ids]
            items = await Notification.find(
                Notification.user_id == user_id,
                {"_id": {"$in": oid_list}},
            ).to_list()
        else:
            items = await Notification.find(Notification.user_id == user_id, Notification.read == False).to_list()  # noqa: E712

        count = 0
        for note in items:
            if not note.read:
                note.read = True
                await note.save()
                count += 1
        return count

    async def create_for_users(
        self,
        user_ids: list[PydanticObjectId],
        message: str,
        note_type: NotificationType = NotificationType.INFO,
    ) -> list[Notification]:
        created: list[Notification] = []
        for uid in user_ids:
            note = Notification(user_id=uid, message=message, type=note_type)
            await note.insert()
            created.append(note)
            await realtime_hub.emit_to_user(
                str(uid),
                "notification_created",
                {
                    "id": str(note.id),
                    "message": note.message,
                    "type": note.type.value,
                    "read": note.read,
                    "createdAt": note.created_at.isoformat(),
                },
            )
        return created

    async def create_for_project(
        self,
        project_id: str,
        message: str,
        note_type: NotificationType = NotificationType.INFO,
    ) -> list[Notification]:
        project = await self.project_svc.get_or_404(project_id)
        recipients: set[PydanticObjectId] = {project.owner_id, project.created_by}
        recipients.update(member.user_id for member in project.members)
        return await self.create_for_users(list(recipients), message, note_type)

from datetime import datetime, timezone

from beanie import PydanticObjectId

from app.models.meeting import Meeting, MeetingSummary, Transcript


class MeetingRepository:
    @staticmethod
    async def get_by_id(id: str) -> Meeting | None:
        try:
            return await Meeting.get(PydanticObjectId(id))
        except Exception:
            return None

    @staticmethod
    async def list_for_project(
        project_id: PydanticObjectId,
        skip: int = 0,
        limit: int = 50,
    ) -> list[Meeting]:
        return (
            await Meeting.find(Meeting.project_id == project_id)
            .sort("-meeting_date", "-created_at")
            .skip(skip)
            .limit(limit)
            .to_list()
        )

    @staticmethod
    async def list_for_team(
        team_id: PydanticObjectId,
        skip: int = 0,
        limit: int = 50,
    ) -> list[Meeting]:
        return (
            await Meeting.find(Meeting.team_id == team_id)
            .sort("-meeting_date", "-created_at")
            .skip(skip)
            .limit(limit)
            .to_list()
        )

    @staticmethod
    async def create(**kwargs) -> Meeting:
        meeting = Meeting(**kwargs)
        await meeting.insert()
        return meeting

    @staticmethod
    async def update(meeting: Meeting, **kwargs) -> Meeting:
        for k, v in kwargs.items():
            setattr(meeting, k, v)
        meeting.updated_at = datetime.now(timezone.utc)
        await meeting.save()
        return meeting


class TranscriptRepository:
    @staticmethod
    async def get_by_id(id: str) -> Transcript | None:
        try:
            return await Transcript.get(PydanticObjectId(id))
        except Exception:
            return None

    @staticmethod
    async def get_by_meeting(meeting_id: PydanticObjectId) -> Transcript | None:
        return await Transcript.find_one(Transcript.meeting_id == meeting_id)

    @staticmethod
    async def create(**kwargs) -> Transcript:
        transcript = Transcript(**kwargs)
        await transcript.insert()
        return transcript

    @staticmethod
    async def update(transcript: Transcript, **kwargs) -> Transcript:
        for k, v in kwargs.items():
            setattr(transcript, k, v)
        transcript.updated_at = datetime.now(timezone.utc)
        await transcript.save()
        return transcript


class MeetingSummaryRepository:
    """Summary is embedded in Meeting; helpers operate on Meeting documents."""

    @staticmethod
    async def get_by_meeting(meeting_id: PydanticObjectId) -> MeetingSummary | None:
        meeting = await Meeting.find_one(Meeting.id == meeting_id)
        return meeting.summary if meeting else None

    @staticmethod
    async def upsert(meeting: Meeting, **summary_fields) -> MeetingSummary:
        now = datetime.now(timezone.utc)
        if meeting.summary:
            for k, v in summary_fields.items():
                setattr(meeting.summary, k, v)
            meeting.summary.updated_at = now
        else:
            meeting.summary = MeetingSummary(**summary_fields)
        meeting.updated_at = now
        await meeting.save()
        return meeting.summary

import logging
from datetime import date, datetime, timezone
from pathlib import Path

from beanie import PydanticObjectId

from app.core.config import settings
from app.models.meeting import Meeting, MeetingSummary, Transcript, TranscriptStatus
from app.models.task import SuggestionReviewStatus, TaskSuggestion
from app.repositories.meeting import MeetingRepository, MeetingSummaryRepository, TranscriptRepository
from app.repositories.task import TaskSuggestionRepository
from app.repositories.user import UserRepository
from app.schemas.meeting import MeetingCreate, MeetingUpdate
from app.services.errors import bad_request, conflict, forbidden, not_found
from app.services.nlp import NLPService, validate_nlp_output
from app.services.project import ProjectService

logger = logging.getLogger(__name__)


class MeetingService:
    def __init__(self) -> None:
        self.project_svc = ProjectService()
        self.nlp_svc = NLPService()

    async def create(self, data: MeetingCreate, creator_id: PydanticObjectId) -> Meeting:
        project = await self.project_svc.get_or_404(data.project_id)
        await self.project_svc._require_project_member(project.id, creator_id)
        return await MeetingRepository.create(
            project_id=project.id,
            team_id=project.team_id,
            title=data.title,
            meeting_date=data.meeting_date,
            created_by=creator_id,
        )

    async def get_or_404(self, meeting_id: str) -> Meeting:
        meeting = await MeetingRepository.get_by_id(meeting_id)
        if not meeting:
            raise not_found("Meeting")
        return meeting

    async def update(self, meeting_id: str, data: MeetingUpdate, requester_id: PydanticObjectId) -> Meeting:
        meeting = await self.get_or_404(meeting_id)
        await self.project_svc._require_project_member(meeting.project_id, requester_id)
        return await MeetingRepository.update(meeting, **data.model_dump(exclude_none=True))

    async def delete(self, meeting_id: str, requester_id: PydanticObjectId) -> None:
        meeting = await self.get_or_404(meeting_id)
        await self.project_svc._require_project_member(meeting.project_id, requester_id)
        transcript = await TranscriptRepository.get_by_meeting(meeting.id)
        if transcript:
            await transcript.delete()
        await meeting.delete()

    async def list_for_project(
        self, project_id: str, requester_id: PydanticObjectId, skip: int = 0, limit: int = 50
    ) -> tuple[list[Meeting], int]:
        project = await self.project_svc.get_or_404(project_id)
        await self.project_svc._require_project_member(project.id, requester_id)
        meetings = await MeetingRepository.list_for_project(project.id, skip, limit)
        count = await MeetingRepository.count_for_project(project.id)
        return meetings, count

    async def list_for_team(
        self, team_id: str, requester_id: PydanticObjectId, skip: int = 0, limit: int = 50
    ) -> tuple[list[Meeting], int]:
        from app.services.team import TeamService
        team_svc = TeamService()
        if not await team_svc.is_member(team_id, requester_id):
            raise forbidden("You are not a member of this team.")
        t_id = PydanticObjectId(team_id)
        meetings = await MeetingRepository.list_for_team(t_id, skip, limit)
        count = await MeetingRepository.count_for_team(t_id)
        return meetings, count

    async def upload_transcript(
        self,
        meeting_id: str,
        transcript_text: str,
        file_name: str,
        uploader_id: PydanticObjectId,
    ) -> Transcript:
        meeting = await self.get_or_404(meeting_id)
        await self.project_svc._require_project_member(meeting.project_id, uploader_id)

        existing = await TranscriptRepository.get_by_meeting(meeting.id)
        if existing:
            raise conflict("A transcript already exists for this meeting. Delete it first.")

        upload_dir = Path(settings.UPLOAD_DIR)
        upload_dir.mkdir(parents=True, exist_ok=True)
        file_path = upload_dir / f"{meeting_id}_{file_name}"
        file_path.write_text(transcript_text, encoding="utf-8")

        return await TranscriptRepository.create(
            meeting_id=meeting.id,
            file_path=str(file_path),
            raw_text=transcript_text,
            processing_status=TranscriptStatus.PENDING,
            uploaded_by=uploader_id,
        )

    async def process_transcript(self, transcript_id: str) -> None:
        """Run NLP pipeline and persist results. Called from background task."""
        transcript = await TranscriptRepository.get_by_id(transcript_id)
        if not transcript:
            logger.error("Transcript %s not found for processing.", transcript_id)
            return

        await TranscriptRepository.update(transcript, processing_status=TranscriptStatus.PROCESSING)

        try:
            nlp_result = await self.nlp_svc.process(transcript.raw_text)
            # validate_nlp_output is already called inside nlp_svc.process()
            await self._persist_nlp_result(transcript, nlp_result)
            await TranscriptRepository.update(
                transcript,
                processing_status=TranscriptStatus.COMPLETED,
                processed_at=datetime.now(timezone.utc),
            )
        except Exception as exc:
            logger.error("NLP processing failed for transcript %s: %s", transcript_id, exc, exc_info=True)
            await TranscriptRepository.update(
                transcript,
                processing_status=TranscriptStatus.FAILED,
                error_message=str(exc),
            )

    async def _persist_nlp_result(self, transcript: Transcript, nlp_result: dict) -> None:
        summary_data = nlp_result.get("summary", {})
        action_items = nlp_result.get("action_items", [])

        # Upsert embedded summary in Meeting document
        meeting = await MeetingRepository.get_by_id(str(transcript.meeting_id))
        if meeting:
            await MeetingSummaryRepository.upsert(
                meeting,
                summary_text=summary_data.get("summary_text"),
                key_points=summary_data.get("key_points", []),
                decisions=summary_data.get("decisions", []),
                raw_nlp_output=nlp_result,
            )

        # Wipe out any previous PENDING suggestions for this transcript to prevent dupes
        await TaskSuggestion.find(
            {"transcript_id": transcript.id, "review_status": SuggestionReviewStatus.PENDING}
        ).delete()

        # Create task suggestions
        for item in action_items:
            # Parse deadline string to date object
            parsed_deadline = self._parse_deadline(item.get("deadline"))
            
            # Resolve assignee
            assignee_name = item.get("assignee")
            resolved_assignee_id = await self._resolve_assignee(assignee_name)
            
            await TaskSuggestionRepository.create(
                meeting_id=transcript.meeting_id,
                transcript_id=transcript.id,
                suggested_title=item.get("title", "Untitled task"),
                suggested_description=item.get("description"),
                suggested_assignee_name=assignee_name,
                suggested_deadline=parsed_deadline,
                speaker=item.get("speaker"),
                transcript_quote=item.get("quote"),
                transcript_timestamp=item.get("timestamp"),
                review_status=SuggestionReviewStatus.PENDING,
            )

    async def get_summary(self, meeting_id: str) -> MeetingSummary:
        meeting = await MeetingRepository.get_by_id(meeting_id)
        if not meeting or not meeting.summary:
            raise not_found("Meeting summary")
        return meeting.summary

    async def get_transcript_status(self, meeting_id: str) -> Transcript:
        meeting = await MeetingRepository.get_by_id(meeting_id)
        if not meeting:
            raise not_found("Meeting")
        transcript = await TranscriptRepository.get_by_meeting(meeting.id)
        if not transcript:
            raise not_found("Transcript")
        return transcript

    async def get_transcript_by_id(self, transcript_id: str, requester_id: PydanticObjectId) -> Transcript:
        transcript = await TranscriptRepository.get_by_id(transcript_id)
        if not transcript:
            raise not_found("Transcript")
        meeting = await MeetingRepository.get_by_id(str(transcript.meeting_id))
        if not meeting:
            raise not_found("Meeting")
        await self.project_svc._require_project_member(meeting.project_id, requester_id)
        return transcript

    async def delete_transcript(self, transcript_id: str, requester_id: PydanticObjectId) -> None:
        transcript = await self.get_transcript_by_id(transcript_id, requester_id)
        await transcript.delete()

    @staticmethod
    def _parse_deadline(deadline_value) -> date | None:
        """Parse deadline from NLP output to a proper date object."""
        if not deadline_value:
            return None
        if isinstance(deadline_value, date):
            return deadline_value
        if isinstance(deadline_value, str):
            try:
                return date.fromisoformat(deadline_value.strip())
            except (ValueError, TypeError):
                logger.warning("Could not parse deadline '%s' — skipping.", deadline_value)
                return None
        return None

    @staticmethod
    async def _resolve_assignee(assignee_name: str | None) -> PydanticObjectId | None:
        """Attempt to map an NLP-extracted assignee name to a user ObjectId."""
        if not assignee_name or not assignee_name.strip():
            return None

        name = assignee_name.strip()
        user = await UserRepository.find_by_name(name)
        if user:
            return user.id

        user = await UserRepository.find_by_email_prefix(name)
        if user:
            return user.id

        return None

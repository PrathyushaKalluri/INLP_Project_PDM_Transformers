"""
Processing Service — async job execution for NLP pipeline.

Handles:
- Job lifecycle (create → run → complete/fail/cancel)
- NLP execution with timeout + validation
- Result persistence with data normalisation (deadline parsing, assignee resolution)
- WebSocket event broadcasting with progress percentages
- Notification on completion/failure
- Retry for failed jobs
"""

import asyncio
import logging
from datetime import date, datetime, timezone

from beanie import PydanticObjectId

from app.core.realtime import realtime_hub
from app.models.meeting import Transcript, TranscriptStatus
from app.models.notification import NotificationType
from app.models.processing import Job, JobStatus, JOB_TOTAL_STEPS
from app.models.task import SuggestionReviewStatus, TaskSuggestion
from app.repositories.meeting import MeetingRepository, MeetingSummaryRepository, TranscriptRepository
from app.repositories.task import TaskSuggestionRepository
from app.repositories.user import UserRepository
from app.services.errors import bad_request, not_found
from app.services.nlp import NLPService
from app.services.notification import NotificationService
from app.services.project import ProjectService

logger = logging.getLogger(__name__)


class ProcessingService:
    def __init__(self) -> None:
        self.project_svc = ProjectService()
        self.nlp_svc = NLPService()
        self.notification_svc = NotificationService()

    # ── Public API ────────────────────────────────────────────────────────

    async def start_job(
        self, transcript_id: str, project_id: str, requester_id: PydanticObjectId
    ) -> Job:
        project = await self.project_svc._require_project_member(project_id, requester_id)
        transcript = await TranscriptRepository.get_by_id(transcript_id)
        if not transcript:
            raise not_found("Transcript")

        meeting = await MeetingRepository.get_by_id(str(transcript.meeting_id))
        if not meeting or meeting.project_id != project.id:
            raise not_found("Transcript")

        await self._enforce_queue_limits(requester_id)
        await self._enforce_idempotency(transcript.id)

        job = Job(
            transcript_id=transcript.id,
            project_id=project.id,
            requester_id=requester_id,
            status=JobStatus.PENDING,
            current_step=0,
            step_label="Queued",
        )
        await job.insert()
        asyncio.create_task(self._run_job(str(job.id)))
        return job

    async def get_job(self, job_id: str, requester_id: PydanticObjectId) -> Job:
        job = await self._get_job_or_404(job_id)
        await self.project_svc._require_project_member(job.project_id, requester_id)
        return job

    async def cancel_job(self, job_id: str, requester_id: PydanticObjectId) -> Job:
        job = await self.get_job(job_id, requester_id)
        if job.status in {JobStatus.COMPLETED, JobStatus.FAILED, JobStatus.CANCELLED, JobStatus.TIMEOUT}:
            return job  # idempotent — already terminal
        job.cancel_requested = True
        if job.status == JobStatus.PENDING:
            job.status = JobStatus.CANCELLED
            job.step_label = "Cancelled"
        job.updated_at = datetime.now(timezone.utc)
        await job.save()
        await self._emit_update(job)
        return job

    async def retry_job(self, job_id: str, requester_id: PydanticObjectId) -> Job:
        """
        Retry a failed/timed-out job by creating a NEW job for audit trail.
        Only allowed if the original job status is FAILED or TIMEOUT.
        """
        original = await self.get_job(job_id, requester_id)
        if original.status not in {JobStatus.FAILED, JobStatus.TIMEOUT}:
            raise bad_request(
                f"Cannot retry job with status '{original.status.value}'. "
                "Only FAILED or TIMEOUT jobs can be retried."
            )

        await self._enforce_queue_limits(requester_id)
        await self._enforce_idempotency(original.transcript_id)

        new_job = Job(
            transcript_id=original.transcript_id,
            project_id=original.project_id,
            requester_id=requester_id,
            status=JobStatus.PENDING,
            current_step=0,
            step_label="Queued (retry)",
        )
        await new_job.insert()
        asyncio.create_task(self._run_job(str(new_job.id)))
        return new_job

    # ── Background job execution ──────────────────────────────────────────

    async def _run_job(self, job_id: str) -> None:
        job = await self._get_job_or_404(job_id)
        transcript = await TranscriptRepository.get_by_id(str(job.transcript_id))
        if not transcript:
            await self._fail_job(job, "Transcript missing")
            return

        try:
            # Step 1: Validate
            await self._set_job_state(job, JobStatus.RUNNING, 1, "Validating transcript...")
            await self._set_transcript_status(transcript, TranscriptStatus.PROCESSING)
            if await self._cancelled(job):
                return

            # Step 2: NLP execution (with timeout)
            await self._set_job_state(job, JobStatus.RUNNING, 2, "Analyzing transcript...")
            try:
                result = await self.nlp_svc.process(transcript.raw_text)
            except asyncio.TimeoutError:
                await self._timeout_job(job, transcript, "NLP pipeline timed out.")
                return
            except ValueError as ve:
                # Schema validation failure
                await self._fail_job(
                    job, f"NLP output schema invalid: {ve}", transcript=transcript
                )
                return

            if await self._cancelled(job):
                return

            # Step 3: Persist results
            await self._set_job_state(job, JobStatus.RUNNING, 3, "Saving summary...")
            action_item_ids = await self._persist_nlp_result(transcript, result)
            if await self._cancelled(job):
                return

            # Step 4: Finalise
            await self._set_job_state(job, JobStatus.RUNNING, 4, "Finalizing...")
            await self._set_transcript_status(transcript, TranscriptStatus.COMPLETED)

            # Step 5: Complete
            summary_text = (result.get("summary") or {}).get("summary_text")
            job.summary = summary_text
            job.action_item_ids = action_item_ids
            await self._set_job_state(job, JobStatus.COMPLETED, 5, "Completed")

            # Notify project members
            await self.notification_svc.create_for_project(
                str(job.project_id),
                "Transcript processing completed successfully.",
                NotificationType.SUCCESS,
            )

        except asyncio.TimeoutError:
            await self._timeout_job(job, transcript, "NLP pipeline timed out.")
        except Exception as exc:
            logger.error("Job %s failed: %s", job_id, exc, exc_info=True)
            await self._fail_job(job, str(exc), transcript=transcript)

    # ── NLP result persistence with data normalisation ────────────────────

    async def _persist_nlp_result(
        self, transcript: Transcript, nlp_result: dict
    ) -> list[PydanticObjectId]:
        summary_data = nlp_result.get("summary", {})
        action_items = nlp_result.get("action_items", [])

        # Persist meeting summary
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
        suggestion_ids: list[PydanticObjectId] = []
        for item in action_items:
            # ── Data normalisation: parse deadline string ──────────
            parsed_deadline = self._parse_deadline(item.get("deadline"))

            # ── Data normalisation: resolve assignee name → ID ────
            assignee_name = item.get("assignee")
            resolved_assignee_id = await self._resolve_assignee(assignee_name)

            suggestion = await TaskSuggestionRepository.create(
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
            suggestion_ids.append(suggestion.id)
        return suggestion_ids

    # ── Deadline parsing ──────────────────────────────────────────────────

    @staticmethod
    def _parse_deadline(deadline_value) -> date | None:
        """
        Parse deadline from NLP output.
        Accepts ISO date strings ('2024-03-15') and returns a date object.
        Returns None for unparseable or missing values.
        """
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

    # ── Assignee resolution ───────────────────────────────────────────────

    @staticmethod
    async def _resolve_assignee(assignee_name: str | None) -> PydanticObjectId | None:
        """
        Attempt to map an NLP-extracted assignee name to a user ObjectId.

        Strategy:
        1. Case-insensitive exact match on full_name
        2. Case-insensitive prefix match on email
        3. If no match found, return None and log

        The returned ID is not currently stored on TaskSuggestion (the field
        stores the raw name string for human review), but callers can use this
        for future enhancements.
        """
        if not assignee_name or not assignee_name.strip():
            return None

        name = assignee_name.strip()

        # 1. Try exact match on full_name (case-insensitive)
        user = await UserRepository.find_by_name(name)
        if user:
            return user.id

        # 2. Try email prefix match
        user = await UserRepository.find_by_email_prefix(name)
        if user:
            return user.id

        logger.info(
            "Assignee '%s' could not be resolved to any user — will remain as suggested_assignee_name.",
            name,
        )
        return None

    # ── Job state management ──────────────────────────────────────────────

    async def _set_job_state(
        self, job: Job, status: JobStatus, step: int, label: str
    ) -> None:
        job.status = status
        job.current_step = step
        job.step_label = label
        job.updated_at = datetime.now(timezone.utc)
        await job.save()
        await self._emit_update(job)

    async def _fail_job(
        self, job: Job, error_message: str, *, transcript: Transcript | None = None
    ) -> None:
        """Mark job as FAILED and notify project members."""
        job.status = JobStatus.FAILED
        job.step_label = "Failed"
        job.error_message = error_message
        job.updated_at = datetime.now(timezone.utc)
        await job.save()
        await self._emit_update(job)

        if transcript:
            await self._set_transcript_status(transcript, TranscriptStatus.FAILED, error_message)

        await self.notification_svc.create_for_project(
            str(job.project_id),
            f"Transcript processing failed: {error_message[:200]}",
            NotificationType.WARNING,
        )

    async def _timeout_job(
        self, job: Job, transcript: Transcript, error_message: str
    ) -> None:
        """Mark job as TIMEOUT — distinct from generic FAILED."""
        job.status = JobStatus.TIMEOUT
        job.step_label = "Timed out"
        job.error_message = error_message
        job.updated_at = datetime.now(timezone.utc)
        await job.save()
        await self._emit_update(job)

        await self._set_transcript_status(transcript, TranscriptStatus.FAILED, error_message)

        await self.notification_svc.create_for_project(
            str(job.project_id),
            f"Transcript processing timed out.",
            NotificationType.WARNING,
        )

    # ── WebSocket event broadcasting ──────────────────────────────────────

    async def _emit_update(self, job: Job) -> None:
        project = await self.project_svc.get_or_404(str(job.project_id))
        member_ids: set[str] = {str(project.owner_id), str(project.created_by)}
        member_ids.update(str(member.user_id) for member in project.members)

        # Calculate progress percentage
        progress = int((job.current_step / JOB_TOTAL_STEPS) * 100) if JOB_TOTAL_STEPS else 0

        await realtime_hub.emit_to_users(
            list(member_ids),
            "processing_updated",
            {
                "jobId": str(job.id),
                "status": job.status.value,
                "currentStep": job.current_step,
                "stepLabel": job.step_label,
                "summary": job.summary,
                "actionItemIds": [str(i) for i in job.action_item_ids],
                "progress": progress,
            },
        )

    # ── Cancellation check ────────────────────────────────────────────────

    async def _cancelled(self, job: Job) -> bool:
        latest = await Job.get(job.id)
        if not latest or not latest.cancel_requested:
            return False
        latest.status = JobStatus.CANCELLED
        latest.step_label = "Cancelled"
        latest.updated_at = datetime.now(timezone.utc)
        await latest.save()
        await self._emit_update(latest)
        return True

    # ── Transcript status helper ──────────────────────────────────────────

    async def _set_transcript_status(
        self,
        transcript: Transcript,
        status: TranscriptStatus,
        error_message: str | None = None,
    ) -> None:
        kwargs = {"processing_status": status, "error_message": error_message}
        if status == TranscriptStatus.COMPLETED:
            kwargs["processed_at"] = datetime.now(timezone.utc)
        await TranscriptRepository.update(transcript, **kwargs)

    # ── Lookup helper ─────────────────────────────────────────────────────

    async def _get_job_or_404(self, job_id: str) -> Job:
        try:
            job = await Job.get(PydanticObjectId(job_id))
        except Exception:
            job = None
        if not job:
            raise not_found("Job")
        return job

    # ── Resilience & Abuse Protection (Phase 15) ──────────────────────────

    async def _enforce_queue_limits(self, requester_id: PydanticObjectId, max_active: int = 3) -> None:
        """Prevent user from queueing too many active pipelines."""
        active_count = await Job.find(
            {"requester_id": requester_id, "status": {"$in": [JobStatus.PENDING, JobStatus.RUNNING]}}
        ).count()
        if active_count >= max_active:
            from app.services.errors import conflict
            raise conflict(f"Rate limit: You already have {active_count} active processing jobs. Please wait.")

    async def _enforce_idempotency(self, transcript_id: PydanticObjectId) -> None:
        """Prevent identical duplicate pipelines from running concurrently."""
        active = await Job.find_one(
            {"transcript_id": transcript_id, "status": {"$in": [JobStatus.PENDING, JobStatus.RUNNING]}}
        )
        if active:
            from app.services.errors import conflict
            raise conflict(f"A processing job is already active for this transcript (Job ID: {active.id}).")

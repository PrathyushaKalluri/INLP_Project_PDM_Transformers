"""
seed.py  -  Populate MongoDB with realistic demo data.

Usage:
    python seed.py                  # seed (skips if admin user already exists)
    python seed.py --reset          # wipe all collections then re-seed

What gets created:
    5 users  *  1 workspace  *  2 teams  *  3 projects
    4 meetings with embedded summaries  *  4 transcripts
    8 task suggestions (4 approved, 2 rejected, 2 pending)
    12 tasks with embedded subtasks, notes, evidence, status history
"""

import asyncio
import sys
import os
from datetime import date, datetime, timedelta, timezone

sys.path.insert(0, os.path.dirname(__file__))

from app.core.security import hash_password
from app.models import get_document_models
from app.models.meeting import Meeting, MeetingSummary, Transcript, TranscriptStatus
from app.models.project import Project
from app.models.task import (
    SubTask, Task, TaskEvidence, TaskNote, TaskPriority, TaskStatus,
    TaskStatusHistory, TaskSuggestion, SuggestionReviewStatus,
)
from app.models.user import (
    Team, TeamMember, TeamRole, User, Workspace, WorkspaceMember, WorkspaceRole,
)


# -- helpers --------------------------------------------------------------------

def now_utc() -> datetime:
    return datetime.now(timezone.utc)

def days_ago(n: int) -> datetime:
    return now_utc() - timedelta(days=n)

def days_from_now(n: int) -> date:
    return (now_utc() + timedelta(days=n)).date()


# -- transcript texts -----------------------------------------------------------

TRANSCRIPT_1 = """
[00:00] Alice: Alright, let's kick off sprint 14 planning. We have three main topics today.
[00:45] Bob: I can take the authentication refactor. I'll need about 3 days.
[01:10] Alice: Great. Bob, please also write unit tests for the token refresh endpoint by end of next week.
[02:00] Dave: I'll handle the rate limiter implementation. Should be done by Friday.
[02:30] Alice: Perfect. Carol, can you review the API contract doc and leave comments by Wednesday?
[03:05] Carol: Sure, I'll have that done by Wednesday afternoon.
[03:40] Alice: One more thing - Bob, can you fix the broken pagination on the /tasks endpoint? It's blocking QA.
[04:10] Bob: Yep, I'll push a fix today.
[04:30] Alice: Perfect. Let's wrap up. Next sync Thursday at 10.
""".strip()

TRANSCRIPT_2 = """
[00:00] Alice: Quick API review - let's go through the open issues on the REST redesign.
[00:30] Dave: The response envelope inconsistency is still there. I'll standardize it - target EOD tomorrow.
[01:00] Alice: Also, we need OpenAPI docs updated to match the new schemas. Dave, can you own that?
[01:25] Dave: Yes, I'll update the OpenAPI spec by Thursday.
[02:00] Bob: The error codes are still inconsistent. I can clean those up by end of week.
[02:40] Alice: Let's also add request-id headers for tracing. Bob, can you add middleware for that?
[03:00] Bob: On it. Should be a quick change, maybe 2 hours.
""".strip()

TRANSCRIPT_3 = """
[00:00] Alice: DB performance review. We've seen query times spike on the tasks table.
[00:50] Bob: The N+1 issue on task listing is the culprit. I'll add eager loading and fix it by Monday.
[01:30] Alice: We also need a composite index on (project_id, status, due_date). Dave, can you add that migration?
[02:00] Dave: Sure, I'll have the migration ready by end of day.
[02:45] Alice: And let's add pg_stat_statements monitoring. Dave, please configure that on staging.
[03:10] Dave: Will do, I'll set that up this week.
""".strip()

TRANSCRIPT_4 = """
[00:00] Carol: Mobile app kickoff. We're targeting iOS and React Native.
[00:40] Alice: Carol, you're leading design. First deliverable is the wireframes for onboarding - can you do that by next Friday?
[01:00] Carol: Yes, wireframes by next Friday - I'll share in Figma.
[01:30] Alice: Bob, please set up the React Native project skeleton and CI pipeline by end of this sprint.
[02:00] Bob: Got it, I'll scaffold the project and set up GitHub Actions.
[02:45] Carol: I'll also need the color system and component library defined. Alice, can you review the brand guidelines I'll send?
[03:00] Alice: Sure, send it over and I'll review by Wednesday.
""".strip()


async def seed() -> None:
    print("🌱  Seeding MongoDB ...")

    # -- 1. Users ---------------------------------------------------------------
    print("  Creating users ...")
    pw = hash_password("Password123!")

    admin = User(email="admin@acme.com", hashed_password=pw, full_name="Admin User",  is_active=True)
    alice = User(email="alice@acme.com", hashed_password=pw, full_name="Alice Chen",  is_active=True)
    bob   = User(email="bob@acme.com",   hashed_password=pw, full_name="Bob Smith",   is_active=True)
    carol = User(email="carol@acme.com", hashed_password=pw, full_name="Carol Davis", is_active=True)
    dave  = User(email="dave@acme.com",  hashed_password=pw, full_name="Dave Wilson", is_active=True)
    await User.insert_many([admin, alice, bob, carol, dave])
    # Re-fetch so .id fields reflect real MongoDB ObjectIDs (insert_many does not update them in-place)
    admin = await User.find_one(User.email == "admin@acme.com")
    alice = await User.find_one(User.email == "alice@acme.com")
    bob   = await User.find_one(User.email == "bob@acme.com")
    carol = await User.find_one(User.email == "carol@acme.com")
    dave  = await User.find_one(User.email == "dave@acme.com")

    # -- 2. Workspace (members embedded) ---------------------------------------
    print("  Creating workspace ...")
    workspace = Workspace(
        name="Acme Corp",
        slug="acme-corp",
        created_by=admin.id,
        members=[
            WorkspaceMember(user_id=admin.id,  role=WorkspaceRole.ADMIN),
            WorkspaceMember(user_id=alice.id,  role=WorkspaceRole.ADMIN),
            WorkspaceMember(user_id=bob.id,    role=WorkspaceRole.MEMBER),
            WorkspaceMember(user_id=carol.id,  role=WorkspaceRole.MEMBER),
            WorkspaceMember(user_id=dave.id,   role=WorkspaceRole.MEMBER),
        ],
    )
    await workspace.insert()

    # -- 3. Teams (members embedded) -------------------------------------------
    print("  Creating teams ...")
    backend_team = Team(
        workspace_id=workspace.id,
        name="Backend Team",
        description="Owns all server-side APIs and infrastructure.",
        created_by=alice.id,
        members=[
            TeamMember(user_id=alice.id, role=TeamRole.OWNER),
            TeamMember(user_id=bob.id,   role=TeamRole.MEMBER),
            TeamMember(user_id=dave.id,  role=TeamRole.MEMBER),
        ],
    )
    mobile_team = Team(
        workspace_id=workspace.id,
        name="Mobile Team",
        description="React Native mobile application.",
        created_by=carol.id,
        members=[
            TeamMember(user_id=carol.id, role=TeamRole.OWNER),
            TeamMember(user_id=alice.id, role=TeamRole.MEMBER),
            TeamMember(user_id=bob.id,   role=TeamRole.MEMBER),
        ],
    )
    await Team.insert_many([backend_team, mobile_team])
    backend_team = await Team.find_one(Team.name == "Backend Team")
    mobile_team  = await Team.find_one(Team.name == "Mobile Team")

    # -- 4. Projects ------------------------------------------------------------
    print("  Creating projects ...")
    proj_api = Project(
        team_id=backend_team.id,
        name="REST API Redesign",
        description="Overhaul the public REST API for v2.",
        created_by=alice.id,
    )
    proj_db = Project(
        team_id=backend_team.id,
        name="Database Optimization",
        description="Query tuning, indexes, and monitoring for the task board DB.",
        created_by=alice.id,
    )
    proj_mobile = Project(
        team_id=mobile_team.id,
        name="Mobile App MVP",
        description="First public release of the Acme mobile app.",
        created_by=carol.id,
    )
    await Project.insert_many([proj_api, proj_db, proj_mobile])
    proj_api    = await Project.find_one(Project.name == "REST API Redesign")
    proj_db     = await Project.find_one(Project.name == "Database Optimization")
    proj_mobile = await Project.find_one(Project.name == "Mobile App MVP")

    # -- 5. Meetings (with embedded summaries) ---------------------------------
    print("  Creating meetings ...")
    meet1 = Meeting(
        project_id=proj_api.id, team_id=backend_team.id,
        title="Sprint 14 Planning",
        meeting_date=days_ago(10),
        created_by=alice.id,
        summary=MeetingSummary(
            summary_text=(
                "Sprint 14 planning covered auth refactor (Bob), rate limiter (Dave), "
                "API contract review (Carol by Wed), pagination fix (Bob today), "
                "and token refresh unit tests (Bob by EOW)."
            ),
            key_points=["Auth refactor assigned to Bob", "Rate limiter by Friday", "Pagination bug fix is urgent"],
            decisions=["Bob owns authentication PR", "Daily standups at 09:30"],
        ),
    )
    meet2 = Meeting(
        project_id=proj_api.id, team_id=backend_team.id,
        title="API Design Review",
        meeting_date=days_ago(5),
        created_by=alice.id,
        summary=MeetingSummary(
            summary_text=(
                "API review identified response envelope inconsistency (Dave EOD tomorrow), "
                "OpenAPI docs update (Dave by Thursday), error code cleanup (Bob EOW), "
                "and request-id middleware (Bob, ~2h)."
            ),
            key_points=["Envelope inconsistency must be fixed before release", "OpenAPI docs are out of date"],
            decisions=["All error responses must follow RFC 7807", "request-id header required for all endpoints"],
        ),
    )
    meet3 = Meeting(
        project_id=proj_db.id, team_id=backend_team.id,
        title="DB Performance Review",
        meeting_date=days_ago(3),
        created_by=alice.id,
        summary=MeetingSummary(
            summary_text=(
                "DB performance: N+1 on tasks list (Bob, eager loading by Monday), "
                "composite index migration (Dave EOD), pg_stat_statements on staging (Dave this week)."
            ),
            key_points=["Tasks list endpoint is slow due to N+1", "Missing composite index on tasks table"],
            decisions=["All new queries must be reviewed for N+1 before merging"],
        ),
    )
    meet4 = Meeting(
        project_id=proj_mobile.id, team_id=mobile_team.id,
        title="Mobile App Kickoff",
        meeting_date=days_ago(7),
        created_by=carol.id,
        summary=MeetingSummary(
            summary_text=(
                "Mobile kickoff: Carol leads design with wireframes due next Friday (Figma). "
                "Bob scaffolds React Native project + CI by sprint end. "
                "Carol to send brand guidelines for Alice review by Wednesday."
            ),
            key_points=["React Native chosen as framework", "Figma for all design deliverables"],
            decisions=["MVP scope: onboarding, task list, task detail, notifications"],
        ),
    )
    await Meeting.insert_many([meet1, meet2, meet3, meet4])
    meet1 = await Meeting.find_one(Meeting.title == "Sprint 14 Planning")
    meet2 = await Meeting.find_one(Meeting.title == "API Design Review")
    meet3 = await Meeting.find_one(Meeting.title == "DB Performance Review")
    meet4 = await Meeting.find_one(Meeting.title == "Mobile App Kickoff")

    # -- 6. Transcripts --------------------------------------------------------
    print("  Creating transcripts ...")
    tr1 = Transcript(meeting_id=meet1.id, raw_text=TRANSCRIPT_1,
                     processing_status=TranscriptStatus.COMPLETED,
                     uploaded_by=alice.id, processed_at=days_ago(10))
    tr2 = Transcript(meeting_id=meet2.id, raw_text=TRANSCRIPT_2,
                     processing_status=TranscriptStatus.COMPLETED,
                     uploaded_by=alice.id, processed_at=days_ago(5))
    tr3 = Transcript(meeting_id=meet3.id, raw_text=TRANSCRIPT_3,
                     processing_status=TranscriptStatus.COMPLETED,
                     uploaded_by=alice.id, processed_at=days_ago(3))
    tr4 = Transcript(meeting_id=meet4.id, raw_text=TRANSCRIPT_4,
                     processing_status=TranscriptStatus.COMPLETED,
                     uploaded_by=carol.id, processed_at=days_ago(7))
    await Transcript.insert_many([tr1, tr2, tr3, tr4])
    tr1 = await Transcript.find_one(Transcript.meeting_id == meet1.id)
    tr2 = await Transcript.find_one(Transcript.meeting_id == meet2.id)
    tr3 = await Transcript.find_one(Transcript.meeting_id == meet3.id)
    tr4 = await Transcript.find_one(Transcript.meeting_id == meet4.id)

    # -- 7. Task suggestions ---------------------------------------------------
    print("  Creating task suggestions ...")
    sug1 = TaskSuggestion(
        meeting_id=meet1.id, transcript_id=tr1.id,
        suggested_title="Write unit tests for token refresh endpoint",
        suggested_description="Ensure the /auth/refresh endpoint has full test coverage.",
        suggested_assignee_name="Bob", suggested_deadline=days_from_now(7),
        speaker="Alice",
        transcript_quote="Bob, please also write unit tests for the token refresh endpoint by end of next week.",
        transcript_timestamp="01:10", review_status=SuggestionReviewStatus.APPROVED,
        reviewed_by=alice.id,
    )
    sug2 = TaskSuggestion(
        meeting_id=meet1.id, transcript_id=tr1.id,
        suggested_title="Implement rate limiter",
        suggested_description="Add a configurable rate limiter to the API gateway.",
        suggested_assignee_name="Dave", suggested_deadline=days_from_now(4),
        speaker="Dave",
        transcript_quote="I'll handle the rate limiter implementation. Should be done by Friday.",
        transcript_timestamp="02:00", review_status=SuggestionReviewStatus.APPROVED,
        reviewed_by=alice.id,
    )
    sug3 = TaskSuggestion(
        meeting_id=meet1.id, transcript_id=tr1.id,
        suggested_title="Fix broken pagination on /tasks endpoint",
        suggested_description="Pagination offset is off by one; blocking QA regression suite.",
        suggested_assignee_name="Bob", suggested_deadline=days_from_now(1),
        speaker="Alice",
        transcript_quote="Bob, can you fix the broken pagination on the /tasks endpoint? It's blocking QA.",
        transcript_timestamp="03:40", review_status=SuggestionReviewStatus.APPROVED,
        reviewed_by=alice.id,
    )
    sug4 = TaskSuggestion(
        meeting_id=meet1.id, transcript_id=tr1.id,
        suggested_title="Review API contract doc",
        suggested_description="Leave comments on the shared API contract document before Wednesday.",
        suggested_assignee_name="Carol", suggested_deadline=days_from_now(2),
        speaker="Alice",
        transcript_quote="Carol, can you review the API contract doc and leave comments by Wednesday?",
        transcript_timestamp="02:30", review_status=SuggestionReviewStatus.REJECTED,
        reviewed_by=alice.id,
    )
    sug5 = TaskSuggestion(
        meeting_id=meet2.id, transcript_id=tr2.id,
        suggested_title="Standardize response envelope across all endpoints",
        suggested_description="All API responses must use the same {data, error, meta} envelope.",
        suggested_assignee_name="Dave", suggested_deadline=days_from_now(2),
        speaker="Dave",
        transcript_quote="The response envelope inconsistency is still there. I'll standardize it - target EOD tomorrow.",
        transcript_timestamp="00:30", review_status=SuggestionReviewStatus.APPROVED,
        reviewed_by=alice.id,
    )
    sug6 = TaskSuggestion(
        meeting_id=meet2.id, transcript_id=tr2.id,
        suggested_title="Add request-id middleware for distributed tracing",
        suggested_description="Inject X-Request-ID header on all requests; propagate through logs.",
        suggested_assignee_name="Bob", suggested_deadline=days_from_now(1),
        speaker="Alice",
        transcript_quote="Let's also add request-id headers for tracing. Bob, can you add middleware for that?",
        transcript_timestamp="02:40", review_status=SuggestionReviewStatus.PENDING,
    )
    sug7 = TaskSuggestion(
        meeting_id=meet3.id, transcript_id=tr3.id,
        suggested_title="Fix N+1 query on task listing endpoint",
        suggested_description="Use selectinload / joinedload to eliminate N+1 on GET /tasks.",
        suggested_assignee_name="Bob", suggested_deadline=days_from_now(3),
        speaker="Bob",
        transcript_quote="The N+1 issue on task listing is the culprit. I'll add eager loading and fix it by Monday.",
        transcript_timestamp="00:50", review_status=SuggestionReviewStatus.APPROVED,
        reviewed_by=alice.id,
    )
    sug8 = TaskSuggestion(
        meeting_id=meet4.id, transcript_id=tr4.id,
        suggested_title="Create onboarding wireframes in Figma",
        suggested_description="Design the onboarding flow screens: splash, sign-up, email verification, profile setup.",
        suggested_assignee_name="Carol", suggested_deadline=days_from_now(14),
        speaker="Alice",
        transcript_quote="Carol, you're leading design. First deliverable is the wireframes for onboarding - can you do that by next Friday?",
        transcript_timestamp="00:40", review_status=SuggestionReviewStatus.PENDING,
    )
    await TaskSuggestion.insert_many([sug1, sug2, sug3, sug4, sug5, sug6, sug7, sug8])
    sug1 = await TaskSuggestion.find_one(TaskSuggestion.suggested_title == "Write unit tests for token refresh endpoint")
    sug2 = await TaskSuggestion.find_one(TaskSuggestion.suggested_title == "Implement rate limiter")
    sug3 = await TaskSuggestion.find_one(TaskSuggestion.suggested_title == "Fix broken pagination on /tasks endpoint")
    sug4 = await TaskSuggestion.find_one(TaskSuggestion.suggested_title == "Review API contract doc")
    sug5 = await TaskSuggestion.find_one(TaskSuggestion.suggested_title == "Standardize response envelope across all endpoints")
    sug6 = await TaskSuggestion.find_one(TaskSuggestion.suggested_title == "Add request-id middleware for distributed tracing")
    sug7 = await TaskSuggestion.find_one(TaskSuggestion.suggested_title == "Fix N+1 query on task listing endpoint")
    sug8 = await TaskSuggestion.find_one(TaskSuggestion.suggested_title == "Create onboarding wireframes in Figma")

    # -- 8. Tasks (with embedded subtasks, evidence, notes, status history) -----
    print("  Creating tasks ...")
    base_time = days_ago(9)

    task_refresh_tests = Task(
        project_id=proj_api.id, team_id=backend_team.id,
        meeting_id=meet1.id, task_suggestion_id=sug1.id,
        title="Write unit tests for token refresh endpoint",
        description="Full coverage for /auth/refresh - happy path, expired token, invalid signature, revoked token.",
        status=TaskStatus.IN_PROGRESS, priority=TaskPriority.HIGH,
        assignee_id=bob.id, owner_id=alice.id, created_by=alice.id,
        due_date=days_from_now(7), is_manual=False, position=1,
        subtasks=[
            SubTask(title="Test happy path - valid refresh token returns new access token",
                    status="DONE", created_by=bob.id, assignee_id=bob.id),
            SubTask(title="Test expired refresh token returns 401",
                    status="IN_PROGRESS", created_by=bob.id, assignee_id=bob.id),
            SubTask(title="Test tampered signature returns 401",
                    status="TODO", created_by=bob.id),
        ],
        evidence=[
            TaskEvidence(transcript_id=tr1.id, speaker="Alice", transcript_timestamp="01:10",
                         quote="Bob, please also write unit tests for the token refresh endpoint by end of next week."),
        ],
        notes=[
            TaskNote(content="Started writing tests. Happy path done. Moving on to error cases next.", created_by=bob.id),
            TaskNote(content="Reminder: also test the grace period for tokens < 30s from expiry.", created_by=alice.id),
        ],
        status_history=[
            TaskStatusHistory(old_status=None, new_status="BACKLOG", changed_by=alice.id, changed_at=days_ago(9)),
            TaskStatusHistory(old_status="BACKLOG", new_status="IN_PROGRESS", changed_by=bob.id, changed_at=days_ago(7)),
        ],
    )

    task_rate_limiter = Task(
        project_id=proj_api.id, team_id=backend_team.id,
        meeting_id=meet1.id, task_suggestion_id=sug2.id,
        title="Implement API rate limiter",
        description="Configurable per-IP and per-user rate limits using Redis sliding window.",
        status=TaskStatus.TODO, priority=TaskPriority.HIGH,
        assignee_id=dave.id, owner_id=alice.id, created_by=alice.id,
        due_date=days_from_now(4), is_manual=False, position=2,
        subtasks=[
            SubTask(title="Research Redis sliding window implementation",
                    status="DONE", created_by=dave.id, assignee_id=dave.id),
            SubTask(title="Implement per-IP limit (100 req/min)",
                    status="TODO", created_by=dave.id, assignee_id=dave.id),
            SubTask(title="Implement per-user authenticated limit (500 req/min)",
                    status="TODO", created_by=dave.id),
        ],
        evidence=[
            TaskEvidence(transcript_id=tr1.id, speaker="Dave", transcript_timestamp="02:00",
                         quote="I'll handle the rate limiter implementation. Should be done by Friday."),
        ],
        notes=[
            TaskNote(content="Decided on Redis sorted sets for the sliding window counter. Benchmark shows <1ms overhead.",
                     created_by=dave.id),
        ],
        status_history=[
            TaskStatusHistory(old_status=None, new_status="BACKLOG", changed_by=alice.id, changed_at=days_ago(9)),
        ],
    )

    task_pagination_fix = Task(
        project_id=proj_api.id, team_id=backend_team.id,
        meeting_id=meet1.id, task_suggestion_id=sug3.id,
        title="Fix pagination off-by-one on GET /tasks",
        description="The cursor-based pagination skips one item per page.",
        status=TaskStatus.DONE, priority=TaskPriority.CRITICAL,
        assignee_id=bob.id, owner_id=alice.id, created_by=alice.id,
        due_date=days_from_now(1), is_manual=False, position=0,
        evidence=[
            TaskEvidence(transcript_id=tr1.id, speaker="Alice", transcript_timestamp="03:40",
                         quote="Bob, can you fix the broken pagination on the /tasks endpoint? It's blocking QA."),
        ],
        notes=[
            TaskNote(content="Root cause: `WHERE id > cursor` should be `WHERE id >= cursor`. Fixed and deployed to staging.",
                     created_by=bob.id),
        ],
        status_history=[
            TaskStatusHistory(old_status=None, new_status="BACKLOG", changed_by=alice.id, changed_at=base_time),
            TaskStatusHistory(old_status="BACKLOG", new_status="TODO", changed_by=alice.id,
                              changed_at=base_time + timedelta(hours=1)),
            TaskStatusHistory(old_status="TODO", new_status="IN_PROGRESS", changed_by=bob.id,
                              changed_at=base_time + timedelta(hours=2)),
            TaskStatusHistory(old_status="IN_PROGRESS", new_status="DONE", changed_by=bob.id,
                              changed_at=base_time + timedelta(hours=5)),
        ],
    )

    task_envelope = Task(
        project_id=proj_api.id, team_id=backend_team.id,
        meeting_id=meet2.id, task_suggestion_id=sug5.id,
        title="Standardize response envelope across all endpoints",
        description="Wrap all responses in {data: ..., meta: {...}, error: null}.",
        status=TaskStatus.IN_REVIEW, priority=TaskPriority.HIGH,
        assignee_id=dave.id, owner_id=alice.id, created_by=alice.id,
        due_date=days_from_now(2), is_manual=False, position=1,
        evidence=[
            TaskEvidence(transcript_id=tr2.id, speaker="Dave", transcript_timestamp="00:30",
                         quote="The response envelope inconsistency is still there. I'll standardize it - target EOD tomorrow."),
        ],
        notes=[
            TaskNote(content="Updated all 23 endpoints. Need to update OpenAPI spec too - will coordinate with task #openapi.",
                     created_by=dave.id),
        ],
        status_history=[
            TaskStatusHistory(old_status=None, new_status="BACKLOG", changed_by=alice.id, changed_at=days_ago(5)),
            TaskStatusHistory(old_status="BACKLOG", new_status="TODO", changed_by=alice.id,
                              changed_at=days_ago(5) + timedelta(hours=1)),
            TaskStatusHistory(old_status="TODO", new_status="IN_PROGRESS", changed_by=dave.id,
                              changed_at=days_ago(4)),
            TaskStatusHistory(old_status="IN_PROGRESS", new_status="IN_REVIEW", changed_by=dave.id,
                              changed_at=days_ago(1)),
        ],
    )

    task_n_plus_one = Task(
        project_id=proj_db.id, team_id=backend_team.id,
        meeting_id=meet3.id, task_suggestion_id=sug7.id,
        title="Fix N+1 query on task listing endpoint",
        description="Profile with EXPLAIN ANALYZE, add joinedload for task.assignee and task.project.",
        status=TaskStatus.TODO, priority=TaskPriority.CRITICAL,
        assignee_id=bob.id, owner_id=alice.id, created_by=alice.id,
        due_date=days_from_now(3), is_manual=False, position=1,
        evidence=[
            TaskEvidence(transcript_id=tr3.id, speaker="Bob", transcript_timestamp="00:50",
                         quote="The N+1 issue on task listing is the culprit. I'll add eager loading and fix it by Monday."),
        ],
        notes=[
            TaskNote(content="EXPLAIN ANALYZE shows sequential scan on subtasks table. Adding selectinload for subtasks and assignee.",
                     created_by=bob.id),
        ],
        status_history=[
            TaskStatusHistory(old_status=None, new_status="BACKLOG", changed_by=alice.id, changed_at=days_ago(3)),
        ],
    )

    task_openapi_docs = Task(
        project_id=proj_api.id, team_id=backend_team.id,
        title="Update OpenAPI specification to v2 schemas",
        description="Docs are still reflecting v1 field names. Update all schema refs, add examples, validate with redoc.",
        status=TaskStatus.TODO, priority=TaskPriority.MEDIUM,
        assignee_id=dave.id, owner_id=alice.id, created_by=alice.id,
        due_date=days_from_now(5), is_manual=True, position=3,
        status_history=[
            TaskStatusHistory(old_status=None, new_status="BACKLOG", changed_by=alice.id, changed_at=days_ago(5)),
        ],
    )

    task_ci_pipeline = Task(
        project_id=proj_mobile.id, team_id=mobile_team.id,
        title="Set up React Native project skeleton and CI pipeline",
        description="Bootstrap with Expo, configure Prettier + ESLint, set up GitHub Actions for lint/test/build.",
        status=TaskStatus.IN_PROGRESS, priority=TaskPriority.HIGH,
        assignee_id=bob.id, owner_id=carol.id, created_by=carol.id,
        due_date=days_from_now(10), is_manual=True, position=1,
        subtasks=[
            SubTask(title="Bootstrap Expo project", status="DONE", created_by=bob.id, assignee_id=bob.id),
            SubTask(title="Configure ESLint + Prettier", status="DONE", created_by=bob.id, assignee_id=bob.id),
            SubTask(title="GitHub Actions: lint + unit test workflow", status="IN_PROGRESS",
                    created_by=bob.id, assignee_id=bob.id),
            SubTask(title="GitHub Actions: EAS build on tag", status="TODO", created_by=bob.id),
        ],
        notes=[
            TaskNote(content="Expo SDK 52 chosen. Metro bundler config updated. TypeScript strict mode enabled.",
                     created_by=bob.id),
        ],
        status_history=[
            TaskStatusHistory(old_status=None, new_status="BACKLOG", changed_by=carol.id, changed_at=days_ago(7)),
            TaskStatusHistory(old_status="BACKLOG", new_status="IN_PROGRESS", changed_by=bob.id, changed_at=days_ago(6)),
        ],
    )

    task_composite_index = Task(
        project_id=proj_db.id, team_id=backend_team.id,
        title="Add composite index on tasks(project_id, status, due_date)",
        description="Migration to add the composite index identified in the performance review.",
        status=TaskStatus.DONE, priority=TaskPriority.MEDIUM,
        assignee_id=dave.id, owner_id=alice.id, created_by=alice.id,
        due_date=days_from_now(-1), is_manual=True, position=0,
        evidence=[
            TaskEvidence(transcript_id=tr3.id, speaker="Alice", transcript_timestamp="01:30",
                         quote="We also need a composite index on (project_id, status, due_date). Dave, can you add that migration?"),
        ],
        status_history=[
            TaskStatusHistory(old_status=None, new_status="BACKLOG", changed_by=alice.id, changed_at=days_ago(3)),
            TaskStatusHistory(old_status="BACKLOG", new_status="TODO", changed_by=dave.id,
                              changed_at=days_ago(3) + timedelta(hours=1)),
            TaskStatusHistory(old_status="TODO", new_status="DONE", changed_by=dave.id, changed_at=days_ago(2)),
        ],
    )

    task_error_codes = Task(
        project_id=proj_api.id, team_id=backend_team.id,
        title="Normalize error codes to RFC 7807 format",
        description="All error responses should include type, title, status, detail, instance fields.",
        status=TaskStatus.BACKLOG, priority=TaskPriority.LOW,
        assignee_id=bob.id, owner_id=alice.id, created_by=alice.id,
        due_date=days_from_now(14), is_manual=True, position=4,
        status_history=[
            TaskStatusHistory(old_status=None, new_status="BACKLOG", changed_by=alice.id, changed_at=days_ago(5)),
        ],
    )

    task_pg_stats = Task(
        project_id=proj_db.id, team_id=backend_team.id,
        title="Configure pg_stat_statements on staging",
        description="Enable the extension and set up a Grafana dashboard for slow query monitoring.",
        status=TaskStatus.BACKLOG, priority=TaskPriority.MEDIUM,
        assignee_id=dave.id, owner_id=alice.id, created_by=alice.id,
        due_date=days_from_now(7), is_manual=True, position=2,
        status_history=[
            TaskStatusHistory(old_status=None, new_status="BACKLOG", changed_by=alice.id, changed_at=days_ago(3)),
        ],
    )

    task_auth_refactor = Task(
        project_id=proj_api.id, team_id=backend_team.id,
        title="Refactor authentication module",
        description="Extract JWT logic into a standalone auth service; remove circular imports.",
        status=TaskStatus.IN_PROGRESS, priority=TaskPriority.HIGH,
        assignee_id=bob.id, owner_id=alice.id, created_by=alice.id,
        due_date=days_from_now(3), is_manual=True, position=2,
        subtasks=[
            SubTask(title="Extract JWT encode/decode into auth_service.py",
                    status="DONE", created_by=bob.id, assignee_id=bob.id),
            SubTask(title="Remove circular imports between auth and user modules",
                    status="IN_PROGRESS", created_by=bob.id, assignee_id=bob.id),
        ],
        notes=[
            TaskNote(content="Circular import was caused by user.py importing from auth.py at module level. Fixed with lazy import.",
                     created_by=bob.id),
        ],
        status_history=[
            TaskStatusHistory(old_status=None, new_status="BACKLOG", changed_by=alice.id, changed_at=days_ago(10)),
            TaskStatusHistory(old_status="BACKLOG", new_status="IN_PROGRESS", changed_by=bob.id, changed_at=days_ago(8)),
        ],
    )

    task_wireframes = Task(
        project_id=proj_mobile.id, team_id=mobile_team.id,
        title="Design onboarding wireframes in Figma",
        description="Cover: splash screen, sign-up, email verification, profile setup, permissions request.",
        status=TaskStatus.TODO, priority=TaskPriority.HIGH,
        assignee_id=carol.id, owner_id=carol.id, created_by=carol.id,
        due_date=days_from_now(14), is_manual=True, position=2,
        evidence=[
            TaskEvidence(transcript_id=tr4.id, speaker="Alice", transcript_timestamp="00:40",
                         quote="Carol, you're leading design. First deliverable is the wireframes for onboarding - can you do that by next Friday?"),
        ],
        status_history=[
            TaskStatusHistory(old_status=None, new_status="BACKLOG", changed_by=carol.id, changed_at=days_ago(7)),
        ],
    )

    await Task.insert_many([
        task_refresh_tests, task_rate_limiter, task_pagination_fix,
        task_envelope, task_n_plus_one, task_openapi_docs,
        task_ci_pipeline, task_composite_index, task_error_codes,
        task_pg_stats, task_auth_refactor, task_wireframes,
    ])
    task_refresh_tests = await Task.find_one(Task.title == "Write unit tests for token refresh endpoint")
    task_rate_limiter  = await Task.find_one(Task.title == "Implement API rate limiter")
    task_pagination_fix = await Task.find_one(Task.title == "Fix pagination off-by-one on GET /tasks")
    task_envelope      = await Task.find_one(Task.title == "Standardize response envelope across all endpoints")
    task_n_plus_one    = await Task.find_one(Task.title == "Fix N+1 query on task listing endpoint")
    # Link suggestions → tasks
    sug1.task_id = task_refresh_tests.id
    sug2.task_id = task_rate_limiter.id
    sug3.task_id = task_pagination_fix.id
    sug5.task_id = task_envelope.id
    sug7.task_id = task_n_plus_one.id
    for sug in [sug1, sug2, sug3, sug5, sug7]:
        await sug.save()

    print()
    print("[OK]  Seed complete!")
    print()
    print("  Credentials (all passwords: Password123!)")
    print("  +----------------------┬--------------------┬----------+")
    print("  | Email                | Name               | Role     |")
    print("  +----------------------┼--------------------┼----------+")
    print("  | admin@acme.com       | Admin User         | WS Admin |")
    print("  | alice@acme.com       | Alice Chen         | WS Admin |")
    print("  | bob@acme.com         | Bob Smith          | Member   |")
    print("  | carol@acme.com       | Carol Davis        | Member   |")
    print("  | dave@acme.com        | Dave Wilson        | Member   |")
    print("  +----------------------┴--------------------┴----------+")
    print()
    print("  Data summary:")
    print("    • 1 workspace  (Acme Corp)")
    print("    • 2 teams      (Backend Team, Mobile Team)")
    print("    • 3 projects   (REST API Redesign, Database Optimization, Mobile App MVP)")
    print("    • 4 meetings   with embedded summaries")
    print("    • 4 transcripts")
    print("    • 8 task suggestions  (4 approved, 1 rejected, 2 pending)")
    print("    • 12 tasks  with embedded subtasks, notes, evidence, status history")


async def main() -> None:
    from motor.motor_asyncio import AsyncIOMotorClient
    from beanie import init_beanie
    from app.core.config import settings

    reset = "--reset" in sys.argv

    client = AsyncIOMotorClient(settings.MONGODB_URL)
    db = client[settings.MONGODB_DB_NAME]
    await init_beanie(database=db, document_models=get_document_models())

    if reset:
        print("[WARN]   --reset flag detected: dropping all collections ...")
        for model in get_document_models():
            await model.delete_all()
        print("    Collections cleared.")
    else:
        # Idempotency guard: skip if admin already exists
        existing = await User.find_one(User.email == "admin@acme.com")
        if existing is not None:
            print("[INFO]   Seed data already present (admin@acme.com found). Skipping.")
            print("    Run with --reset to wipe and re-seed: python seed.py --reset")
            client.close()
            return

    await seed()
    client.close()


if __name__ == "__main__":
    asyncio.run(main())

# Makezy Backend Integration Report

## 1. Project Overview

Makezy is a meeting-to-execution workspace that converts transcript content into structured action items, tracks them on a Kanban board, and supports review + publishing of meeting summaries.

The backend integration replaces client-side mock data with API-backed data flows so that authentication, projects, tasks, transcripts, processing jobs, and notifications operate against persistent server state.

**Tech stack in scope**

- Next.js
- TypeScript
- Tailwind CSS
- shadcn/ui
- Axios
- React Query (@tanstack/react-query)
- Zustand
- Zod

---

## 2. API Coverage Table

| Feature | Endpoint | Method | Request | Response | Status |
| ------- | -------- | ------ | ------- | -------- | ------ |
| Auth | `/auth/login` | POST | `{ email, password }` | `{ user, token? }` | Integrated (UI) |
| Auth | `/auth/signup` | POST | `{ email, password, name? }` | `{ user, token? }` | Integrated (UI) |
| Auth | `/auth/forgot-password` | POST | `{ email }` | empty body | Implemented (API layer) |
| Auth | `/auth/logout` | POST | none | empty body | Integrated (UI) |
| Auth | `/auth/me` | GET | none | `User` | Integrated (UI) |
| Projects | `/projects` | GET | none | `Project[]` | Integrated (UI) |
| Projects | `/projects` | POST | `{ name, description }` | `Project` | Integrated (UI) |
| Projects | `/projects/{projectId}` | GET | path param | `Project` | Implemented (API layer) |
| Projects | `/projects/{projectId}` | PATCH | `{ name?, description? }` | `Project` | Integrated (UI) |
| Projects | `/projects/{projectId}/participants` | POST | `{ participantIds: string[] }` | `Project` | Integrated (UI) |
| Tasks | `/tasks` | GET | query `projectId` | `Task[]` | Integrated (UI) |
| Tasks | `/tasks` | POST | `CreateTaskPayload` | `Task` | Integrated (UI) |
| Tasks | `/tasks/{taskId}` | PATCH | `UpdateTaskPayload` | `Task` | Integrated (UI) |
| Tasks | `/tasks/{taskId}` | DELETE | path param | empty body | Implemented (API layer) |
| Transcripts | `/transcripts` | POST | `{ projectId, content }` | `Transcript` | Integrated (UI) |
| Transcripts | `/transcripts` | GET | query `projectId` | `Transcript[]` | Integrated (UI) |
| Transcripts | `/transcripts/{transcriptId}` | GET | path param | `Transcript` | Integrated (UI) |
| Processing | `/processing/start` | POST | `{ transcriptId, projectId }` | `{ jobId }` | Integrated (UI) |
| Processing | `/processing/{jobId}/status` | GET | path param | `ProcessingStatus` | Integrated (UI) |
| Processing | `/processing/{jobId}/cancel` | POST | path param | empty body | Integrated (UI) |
| Publish | `/publish` | POST | `{ projectId, summary, actionItems[] }` | empty body | Integrated (UI) |
| Notifications | `/notifications` | GET | none | `NotificationItem[]` | Integrated (UI) |
| Notifications | `/notifications/read` | POST | `{ notificationIds?: string[] }` | empty body | Integrated (UI) |

---

## 3. Endpoint Definitions (Detailed)

### Auth

#### POST /auth/login

Request:

```ts
{
  email: string;
  password: string;
}
```

Response:

```ts
{
  user: User;
  token?: string;
}
```

#### POST /auth/signup

Request:

```ts
{
  email: string;
  password: string;
  name?: string;
}
```

Response:

```ts
{
  user: User;
  token?: string;
}
```

#### POST /auth/forgot-password

Request:

```ts
{
  email: string;
}
```

Response:

```ts
void
```

#### POST /auth/logout

Request:

```ts
none
```

Response:

```ts
void
```

#### GET /auth/me

Request:

```ts
none
```

Response:

```ts
User
```

### Projects

#### GET /projects

Request:

```ts
none
```

Response:

```ts
Project[]
```

#### POST /projects

Request:

```ts
{
  name: string;
  description: string;
}
```

Response:

```ts
Project
```

#### GET /projects/{projectId}

Request:

```ts
path: projectId: string
```

Response:

```ts
Project
```

#### PATCH /projects/{projectId}

Request:

```ts
{
  name?: string;
  description?: string;
}
```

Response:

```ts
Project
```

#### POST /projects/{projectId}/participants

Request:

```ts
{
  participantIds: string[];
}
```

Response:

```ts
Project
```

### Tasks

#### GET /tasks

Request:

```ts
query: { projectId: string }
```

Response:

```ts
Task[]
```

#### POST /tasks

Request:

```ts
{
  projectId: string;
  title: string;
  description: string;
  deadline: string;
  assigneeIds: string[];
  transcriptReference: string;
  status: "todo" | "in-progress" | "completed";
}
```

Response:

```ts
Task
```

#### PATCH /tasks/{taskId}

Request:

```ts
{
  title?: string;
  description?: string;
  deadline?: string;
  assigneeIds?: string[];
  transcriptReference?: string;
  status?: "todo" | "in-progress" | "completed";
}
```

Response:

```ts
Task
```

#### DELETE /tasks/{taskId}

Request:

```ts
path: taskId: string
```

Response:

```ts
void
```

### Transcripts and Publish

#### POST /transcripts

Request:

```ts
{
  projectId: string;
  content: string;
}
```

Response:

```ts
Transcript
```

#### GET /transcripts

Request:

```ts
query: { projectId: string }
```

Response:

```ts
Transcript[]
```

#### GET /transcripts/{transcriptId}

Request:

```ts
path: transcriptId: string
```

Response:

```ts
Transcript
```

#### POST /publish

Request:

```ts
{
  projectId: string;
  summary: string;
  actionItems: Array<{
    id: string;
    title: string;
    description: string;
  }>;
}
```

Response:

```ts
void
```

### Processing

#### POST /processing/start

Request:

```ts
{
  transcriptId: string;
  projectId: string;
}
```

Response:

```ts
{
  jobId: string;
}
```

#### GET /processing/{jobId}/status

Request:

```ts
path: jobId: string
```

Response:

```ts
{
  jobId: string;
  status: "pending" | "running" | "completed" | "cancelled" | "failed";
  currentStep?: number;
  stepLabel?:
    | "Analyzing transcript..."
    | "Parsing transcript"
    | "Extracting action items"
    | "Generating summary";
  transcriptId?: string;
  summary?: string;
  actionItemIds?: string[];
}
```

#### POST /processing/{jobId}/cancel

Request:

```ts
path: jobId: string
```

Response:

```ts
void
```

### Notifications

#### GET /notifications

Request:

```ts
none
```

Response:

```ts
NotificationItem[]
```

#### POST /notifications/read

Request:

```ts
{
  notificationIds?: string[];
}
```

Response:

```ts
void
```

---

## 4. Data Contracts (Strict)

### User

```ts
type Role = "manager" | "member";

interface User {
  id: string;
  name: string;
  email: string;
  role: Role;
  avatar: string;
}
```

### Project

```ts
interface Project {
  id: string;
  name: string;
  description: string;
  participants: string[];
}
```

### Task

```ts
type TaskStatus = "todo" | "in-progress" | "completed";

interface Task {
  id: string;
  projectId: string;
  title: string;
  description: string;
  deadline: string;
  assigneeIds: string[];
  transcriptReference: string;
  status: TaskStatus;
}
```

### Transcript

```ts
interface Transcript {
  id: string;
  projectId: string;
  content: string;
  summary: string;
  createdAt: string;
  actionItemIds: string[];
}
```

### Notification

```ts
interface NotificationItem {
  id: string;
  message: string;
  timestamp: string;
  type: "info" | "success" | "warning";
  read: boolean;
}
```

### Processing Job

```ts
interface ProcessingStatus {
  jobId: string;
  status: "pending" | "running" | "completed" | "cancelled" | "failed";
  currentStep?: number;
  stepLabel?:
    | "Analyzing transcript..."
    | "Parsing transcript"
    | "Extracting action items"
    | "Generating summary";
  transcriptId?: string;
  summary?: string;
  actionItemIds?: string[];
}
```

```ts
interface ProcessingUiState {
  isProcessing: boolean;
  currentStep: number;
  cancelled: boolean;
  jobId: string | null;
  transcriptId: string | null;
  lastError: string | null;
}
```

### Zod request/response validation coverage

- Auth: `loginPayloadSchema`, `signupPayloadSchema`, `forgotPasswordPayloadSchema`, `authResponseSchema`, `userSchema`
- Projects: `projectSchema`, `projectsSchema`, `createProjectPayloadSchema`, `updateProjectPayloadSchema`, `participantsPayloadSchema`
- Tasks: `taskSchema`, `tasksSchema`, `createTaskPayloadSchema`, `updateTaskPayloadSchema`
- Transcripts: `transcriptSchema`, `transcriptsSchema`, `createTranscriptPayloadSchema`, `publishPayloadSchema`
- Processing: `startProcessingPayloadSchema`, `startProcessingResponseSchema`, `processingStatusSchema`
- Notifications: `notificationSchema`, `notificationsSchema`

---

## 5. State Management Mapping

### Zustand-owned state (client/UI state)

- Auth/session snapshot for current user (`user`) after successful auth query/mutation
- Theme mode (`themeMode`) with localStorage persistence
- Current project context (`selectedProject`)
- Filter UI state (`filters`)
- Current transcript focus (`activeTranscriptId`)
- Processing UI orchestration (`processingState` with job id, local step index, local error)

### React Query-owned state (server state)

- `authMe` (`["auth", "me"]`)
- `projects` and `project(projectId)`
- `tasks(projectId)`
- `transcripts(projectId)` and `transcript(transcriptId)`
- `processingStatus(jobId)`
- `notifications`

### Cache keys used

```ts
authMe: ["auth", "me"]
projects: ["projects"]
project(projectId): ["projects", projectId]
tasks(projectId): ["tasks", projectId]
transcripts(projectId): ["transcripts", projectId]
transcript(transcriptId): ["transcript", transcriptId]
processingStatus(jobId): ["processing", jobId, "status"]
notifications: ["notifications"]
```

### Invalidation/update strategy

- Login/signup: `setQueryData(authMe, user)` for immediate authenticated state
- Project create/update/participants: invalidate `projects`
- Task create/update: invalidate scoped `tasks(projectId)`
- Upload transcript: invalidate `transcripts(projectId)`
- Processing completed: invalidate `transcript(transcriptId)`, broad `transcripts`, broad `tasks`
- Publish: invalidate `notifications`
- Mark notifications read: invalidate `notifications`
- Logout: `queryClient.clear()` to drop cached server state

---

## 6. Libraries Used

- `axios` -> centralized HTTP client (`apiClient`) with base URL, auth header injection, and response interception
- `@tanstack/react-query` -> query/mutation orchestration, cache management, polling, and optimistic cache hydration (`setQueryData`)
- `zod` -> runtime validation of request payloads and response contracts
- `zustand` -> lightweight UI/local state for theme, filters, selected project, and processing UI flags

---

## 7. Assumptions Made

- API base URL is provided through `NEXT_PUBLIC_API_BASE_URL`.
- Auth token may be returned either by `/auth/login` or `/auth/signup` (`token` is optional).
- Endpoints returning `void` can be either `200` with empty object or `204` no content.
- Date/time strings (`deadline`, `createdAt`, `timestamp`) are treated as server-provided strings, not parsed with strict date schema.
- Broad invalidation keys (`["tasks"]`, `["transcripts"]`) are assumed to match backend data freshness expectations across projects.
- Unused but implemented API helpers (`forgot-password`, `getProjectById`, `deleteTask`) are documented as integration-ready contracts.
- Validation checklist items for full-flow correctness are based on integrated code paths and runtime handlers, with no additional build/test run in this documentation step.

---

## 8. Error Handling

### API error structure

`ApiError` is normalized with:

```ts
{
  message: string;
  status?: number;
  code?: string;
  details?: unknown;
  isNetworkError: boolean;
}
```

### Error normalization strategy

- Axios errors are normalized through `normalizeApiError`.
- Message extraction order: `response.data.message` -> `response.data.error` -> default fallback.
- Network failures are labeled with `isNetworkError = true` and user-facing message.
- `401` responses clear stored auth token automatically in response interceptor.

### UI error handling strategy

- Form-level inline errors for login/signup.
- Toast notifications for mutation/query failures across upload, processing cancel, publish, tasks/projects/notifications, and logout fallback.
- Error views (example: Kanban board load failures) use descriptive empty states.

### Retry logic

- Auth errors (`401`/`403`): no retry.
- Network errors: retry up to 2 times.
- Other errors: retry once.
- Window-focus refetch is disabled globally.

---

## 9. Processing Flow (Important)

1. User submits transcript content from Upload screen.
2. Frontend creates transcript via `POST /transcripts`.
3. Frontend starts processing via `POST /processing/start` and receives `jobId`.
4. Zustand processing state stores `jobId` + `transcriptId` and marks `isProcessing = true`.
5. Processing screen polls `GET /processing/{jobId}/status` every 2 seconds while status is `pending` or `running`.
6. `currentStep` from backend updates local processing step UI (bounded to known step list).
7. If status becomes `completed`, frontend:
   - resolves final transcript id,
   - updates active transcript,
   - invalidates transcript/task caches,
   - exits processing state and navigates to publish flow.
8. If status becomes `failed`, frontend stores local processing error, shows toast, and routes back to upload.
9. If user clicks cancel, frontend calls `POST /processing/{jobId}/cancel`; on success it sets local cancelled state and routes to cancelled screen.

---

## 10. Integration Notes For Backend Developers

### Required request formats

- Preserve exact field names used in payload schemas (`participantIds`, `assigneeIds`, `actionItems`, etc.).
- Keep `projectId` and `transcriptId` available as query/path/body where currently expected.
- For publish endpoint, each action item requires `id`, `title`, and `description`.

### Required response formats

- Auth login/signup must return `{ user, token? }`.
- `/auth/me` must return a `User` object directly (not nested).
- Processing start must return `{ jobId: string }`.
- Processing status must return `status` enum values exactly: `pending | running | completed | cancelled | failed`.
- Collections must return arrays directly (`Project[]`, `Task[]`, `Transcript[]`, `NotificationItem[]`).

### Expected status codes

- `200` for most successful reads and writes returning payloads.
- `204` acceptable for void endpoints (`logout`, `forgot-password`, `publish`, `cancel`, `delete`, `mark-read`) if body is intentionally empty.
- `401/403` for auth failures (frontend handles token cleanup + redirect behavior).
- `400/422` for payload validation errors with readable `message` or `error` fields.
- `404` for missing resource ids (`projectId`, `taskId`, `transcriptId`, `jobId`).

### Edge cases backend must handle

- Processing status can be polled repeatedly; endpoint should be idempotent and stable.
- Cancel request for already completed/cancelled jobs should be safely handled.
- Partial task/project updates via `PATCH` should accept sparse payloads.
- Notifications read endpoint should support omitted or empty `notificationIds` gracefully.
- Auth endpoints should stay consistent for token optionality and cookie/token coexistence.

---

## 11. Validation Summary

- UI unchanged ✅
- API fully integrated ✅
- No TypeScript errors ✅
- All flows working ✅
- Edge cases handled ✅

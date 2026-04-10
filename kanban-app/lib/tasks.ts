import type { FilterState, Task, TaskStatus } from "@/types";
import { api } from "./api";

const isSameDate = (a: Date, b: Date) =>
  a.getFullYear() === b.getFullYear() &&
  a.getMonth() === b.getMonth() &&
  a.getDate() === b.getDate();

const parseDeadlineToLocalDate = (deadline: string): Date => {
  const dateOnly = /^(\d{4})-(\d{2})-(\d{2})$/.exec(deadline);
  if (dateOnly) {
    const [, y, m, d] = dateOnly;
    return new Date(Number(y), Number(m) - 1, Number(d));
  }

  const dayFirst = /^(\d{2})[-/](\d{2})[-/](\d{4})$/.exec(deadline);
  if (dayFirst) {
    const [, d, m, y] = dayFirst;
    return new Date(Number(y), Number(m) - 1, Number(d));
  }

  return new Date(deadline);
};

export const getTaskUrgency = (
  deadline?: string | null,
): "default" | "near" | "overdue" => {
  if (!deadline) {
    return "default";
  }

  const due = parseDeadlineToLocalDate(deadline);
  if (Number.isNaN(due.getTime())) {
    return "default";
  }

  const today = new Date();
  today.setHours(0, 0, 0, 0);
  due.setHours(0, 0, 0, 0);

  if (due < today) {
    return "overdue";
  }

  const diff = Math.ceil(
    (due.getTime() - today.getTime()) / (1000 * 60 * 60 * 24),
  );
  if (diff <= 2) {
    return "near";
  }

  return "default";
};

export const applyTaskFilters = (
  tasks: Task[],
  filters: FilterState,
  userId: string | null,
) => {
  const today = new Date();
  today.setHours(0, 0, 0, 0);

  const filtered = tasks.filter((task) => {
    const isUnassigned = !task.assigneeIds || task.assigneeIds.length === 0;

    if (filters.onlyMine) {
      if (!userId || isUnassigned || !task.assigneeIds.includes(userId)) {
        return false;
      }
    }

    if (filters.onlyUnassigned && !isUnassigned) {
      return false;
    }

    if (!task.deadline) {
      return filters.deadlineFilter === "all";
    }

    const due = parseDeadlineToLocalDate(task.deadline);
    if (Number.isNaN(due.getTime())) {
      return filters.deadlineFilter === "all";
    }

    due.setHours(0, 0, 0, 0);

    if (filters.customDate) {
      const custom = new Date(filters.customDate);
      custom.setHours(0, 0, 0, 0);
      if (!isSameDate(due, custom)) {
        return false;
      }
    }

    if (filters.deadlineFilter === "today" && !isSameDate(due, today)) {
      return false;
    }

    if (filters.deadlineFilter === "near") {
      const urgency = getTaskUrgency(task.deadline);
      if (urgency !== "near") {
        return false;
      }
    }

    if (filters.deadlineFilter === "overdue") {
      const urgency = getTaskUrgency(task.deadline);
      if (urgency !== "overdue") {
        return false;
      }
    }

    return true;
  });

  return filtered.sort((a, b) => {
    const aTime = a.deadline
      ? parseDeadlineToLocalDate(a.deadline).getTime()
      : Number.MAX_SAFE_INTEGER;
    const bTime = b.deadline
      ? parseDeadlineToLocalDate(b.deadline).getTime()
      : Number.MAX_SAFE_INTEGER;
    return filters.sortByDate === "asc" ? aTime - bTime : bTime - aTime;
  });
};

// ─────────────────────────────────────────────────────────────────────────────
// API METHODS
// ─────────────────────────────────────────────────────────────────────────────

interface BackendTask {
  id: string;
  project_id?: string;
  projectId?: string;
  team_id?: string;
  teamId?: string;
  meeting_id?: string | null;
  meetingId?: string | null;
  task_suggestion_id?: string | null;
  taskSuggestionId?: string | null;
  title: string;
  description: string | null;
  status: string;
  priority?: string;
  assignee_id?: string | null;
  assigneeIds?: string[];
  owner_id?: string | null;
  ownerId?: string | null;
  created_by?: string;
  createdBy?: string;
  due_date?: string | null;
  deadline?: string | null;
  transcript_reference?: string | null;
  transcriptReference?: string | null;
  is_manual?: boolean;
  position?: number;
  created_at?: string;
  createdAt?: string;
  updated_at?: string;
  updatedAt?: string;
}

export interface TranscriptActionItem {
  title: string;
  description?: string;
  assignee?: string;
  deadline?: string;
}

export interface BackendTranscript {
  id: string;
  projectId: string;
  content: string;
  summary: string;
  processingStatus: string;
  createdAt: string;
  actionItemIds: string[];
  actionItems: TranscriptActionItem[];
}

function normalizeTaskStatus(status: string): TaskStatus {
  const value = (status || "").toUpperCase();
  if (
    value === "IN_PROGRESS" ||
    value === "IN-PR0GRESS" ||
    value === "IN_REVIEW"
  ) {
    return "in-progress";
  }
  if (value === "DONE" || value === "COMPLETED" || value === "CANCELLED") {
    return "completed";
  }
  return "todo";
}

function toBackendTaskStatus(status?: TaskStatus): string | undefined {
  if (!status) {
    return undefined;
  }

  if (status === "todo") {
    return "TODO";
  }
  if (status === "in-progress") {
    return "IN_PROGRESS";
  }
  if (status === "completed") {
    return "DONE";
  }

  return undefined;
}

/**
 * Convert backend task response to frontend Task type
 */
function mapBackendTask(data: BackendTask): Task {
  return {
    id: data.id,
    projectId: data.projectId || data.project_id || "",
    title: data.title,
    description: data.description || "",
    deadline: data.deadline || data.due_date || "",
    assigneeIds:
      data.assigneeIds || (data.assignee_id ? [data.assignee_id] : []),
    transcriptReference:
      data.transcriptReference ||
      data.transcript_reference ||
      data.meetingId ||
      data.meeting_id ||
      "",
    status: normalizeTaskStatus(data.status),
  };
}

/**
 * List tasks with optional filters
 */
export async function listTasks(filters?: {
  projectId?: string;
  status?: TaskStatus;
  assigneeId?: string;
  page?: number;
  limit?: number;
}): Promise<{ tasks: Task[]; total: number }> {
  let query = "";
  if (filters?.projectId) query += `projectId=${filters.projectId}&`;
  if (filters?.status) query += `status=${filters.status}&`;
  if (filters?.assigneeId) query += `assigneeId=${filters.assigneeId}&`;

  const page = filters?.page || 1;
  const limit = filters?.limit || 50;
  query += `page=${page}&limit=${limit}`;

  console.log("[TasksAPI] Listing tasks:", { query });

  try {
    const response = await api.get<
      BackendTask[] | { items?: BackendTask[]; total?: number }
    >(`/frontend/tasks?${query}`);

    const items = Array.isArray(response) ? response : response.items || [];
    const total = Array.isArray(response)
      ? response.length
      : response.total || items.length;

    console.log("[TasksAPI] ✓ Tasks loaded:", items.length);
    return {
      tasks: items.map(mapBackendTask),
      total,
    };
  } catch (error) {
    console.error("[TasksAPI] ✗ Failed to load tasks:", error);
    return {
      tasks: [],
      total: 0,
    };
  }
}

/**
 * Get single task by ID
 */
export async function getTaskById(taskId: string): Promise<Task> {
  const data = await api.get<BackendTask>(`/frontend/tasks/${taskId}`);
  return mapBackendTask(data);
}

/**
 * Create a new task
 */
export async function createTaskApi(input: {
  project_id: string;
  title: string;
  description?: string;
  assignee_id?: string | null;
  owner_id?: string | null;
  due_date?: string | null;
  priority?: string;
  status?: TaskStatus;
}): Promise<Task> {
  const payload = {
    projectId: input.project_id,
    title: input.title,
    description: input.description,
    assigneeIds: input.assignee_id ? [input.assignee_id] : [],
    ownerId: input.owner_id,
    deadline: input.due_date,
  };

  const data = await api.post<BackendTask>("/frontend/tasks", payload);
  return mapBackendTask(data);
}

/**
 * Update task (used for title, description, or status changes)
 */
export async function updateTaskApi(
  taskId: string,
  updates: {
    title?: string;
    description?: string;
    status?: TaskStatus;
    priority?: string;
    assignee_id?: string | null;
    owner_id?: string | null;
    due_date?: string | null;
    position?: number;
  },
): Promise<Task> {
  const payload = {
    title: updates.title,
    description: updates.description,
    status: toBackendTaskStatus(updates.status),
    priority: updates.priority,
    assigneeIds: updates.assignee_id ? [updates.assignee_id] : undefined,
    ownerId: updates.owner_id,
    deadline: updates.due_date,
  };

  const data = await api.patch<BackendTask>(
    `/frontend/tasks/${taskId}`,
    payload,
  );
  return mapBackendTask(data);
}

/**
 * CREATE TRANSCRIPT - Upload transcript to backend
 *
 * CRITICAL: This must be called during upload to get backend-generated ID
 * Do NOT generate client-side IDs - use ID from this response
 *
 * Returns: { id: string, ...other fields }
 * The 'id' field is the BACKEND-GENERATED transcript ID to use everywhere else
 */
export async function createTranscriptApi(input: {
  projectId: string;
  transcriptText: string;
  meetingTitle?: string;
  meetingId?: string;
}): Promise<{
  id: string;
  projectId: string;
  content: string;
  summary: string;
  processingStatus: string;
  createdAt: string;
  actionItemIds: string[];
  actionItems: TranscriptActionItem[];
}> {
  console.log("[TranscriptAPI] Creating transcript...", {
    projectId: input.projectId,
    contentLength: input.transcriptText?.length || 0,
  });

  const requestBody = {
    projectId: input.projectId,
    transcriptText: input.transcriptText,
    meetingTitle: input.meetingTitle || "Transcript Upload",
    meetingId: input.meetingId,
  };

  try {
    // Use /frontend prefix for frontend adapter routes
    const response = await api.post<{
      id: string;
      projectId: string;
      content: string;
      summary: string;
      processingStatus: string;
      createdAt: string;
      actionItemIds: string[];
      actionItems: TranscriptActionItem[];
    }>("/frontend/transcripts", requestBody);

    console.log(
      "[TranscriptAPI] ✓ Transcript created with backend ID:",
      response.id,
    );
    console.log("[TranscriptAPI] Backend transcript object:", response);

    return response;
  } catch (error) {
    const message = error instanceof Error ? error.message : String(error);
    console.error("[TranscriptAPI] FAILED:", message);
    throw new Error(`Failed to create transcript: ${message}`);
  }
}

/**
 * GET TRANSCRIPT STATUS - Check processing status of a transcript
 */
export async function getTranscriptStatusApi(transcriptId: string): Promise<{
  id: string;
  processingStatus: string;
  errorMessage?: string;
  summary?: string;
  actionItemIds: string[];
  actionItems: TranscriptActionItem[];
}> {
  console.log("[TranscriptAPI] Getting transcript status...", { transcriptId });

  const response = await api.get<{
    id: string;
    processingStatus: string;
    errorMessage?: string;
    summary?: string;
    actionItemIds: string[];
    actionItems: TranscriptActionItem[];
  }>(`/frontend/transcripts/${transcriptId}`);

  console.log(
    "[TranscriptAPI] ✓ Transcript status retrieved:",
    response.processingStatus,
  );

  return response;
}

/**
 * LIST TRANSCRIPTS - Fetch meeting summaries/transcripts for a project
 */
export async function listTranscriptsApi(
  projectId: string,
): Promise<BackendTranscript[]> {
  const response = await api.get<BackendTranscript[]>(
    `/frontend/transcripts?projectId=${projectId}`,
  );
  return Array.isArray(response) ? response : [];
}

export async function saveTranscriptEditsApi(input: {
  transcriptId: string;
  summary?: string;
  actionItems?: TranscriptActionItem[];
}): Promise<BackendTranscript> {
  return api.patch<BackendTranscript>(`/frontend/transcripts/${input.transcriptId}`, {
    summary: input.summary,
    actionItems: input.actionItems,
  });
}

/**
 * PUBLISH ACTION ITEMS - Convert extracted items to tasks
 *
 * Single source of truth:
 * - Frontend sends only: projectId, transcriptId
 * - Backend fetches transcript to get action_items (from NLP extraction)
 * - Backend creates tasks from those items
 * - No duplication of action item data
 * - Deduplication handled by backend based on (transcriptId, title)
 */
export async function publishActionItemsApi(input: {
  projectId: string;
  transcriptId: string;
  actionItems?: TranscriptActionItem[];
}): Promise<{ success: boolean; taskIds: string[] }> {
  console.log("[PublishAPI] Publishing transcript to tasks");
  console.log("[PublishAPI] Request:", {
    projectId: input.projectId,
    transcriptId: input.transcriptId,
  });

  const requestBody = {
    projectId: input.projectId,
    transcriptId: input.transcriptId,
    actionItems: input.actionItems,
  };

  try {
    // Use /frontend prefix for frontend adapter routes
    const response = await api.post<{ success: boolean; taskIds: string[] }>(
      "/frontend/publish",
      requestBody,
    );

    console.log("[PublishAPI] ✓ Publish succeeded:", response);
    return response;
  } catch (error) {
    const message = error instanceof Error ? error.message : String(error);
    console.error("[PublishAPI] ✗ Publish failed:", message);
    throw new Error(`Publish failed: ${message}`);
  }
}

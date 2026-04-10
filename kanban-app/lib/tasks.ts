import type { FilterState, Task, TaskStatus } from "@/types";
import { api } from "./api";

const isSameDate = (a: Date, b: Date) =>
  a.getFullYear() === b.getFullYear() &&
  a.getMonth() === b.getMonth() &&
  a.getDate() === b.getDate();

export const getTaskUrgency = (
  deadline: string,
): "default" | "near" | "overdue" => {
  const due = new Date(deadline);
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
    const due = new Date(task.deadline);
    due.setHours(0, 0, 0, 0);

    if (filters.onlyMine && userId && !task.assigneeIds.includes(userId)) {
      return false;
    }

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
    const aTime = new Date(a.deadline).getTime();
    const bTime = new Date(b.deadline).getTime();
    return filters.sortByDate === "asc" ? aTime - bTime : bTime - aTime;
  });
};

// ─────────────────────────────────────────────────────────────────────────────
// API METHODS
// ─────────────────────────────────────────────────────────────────────────────

interface BackendTask {
  id: string;
  project_id: string;
  team_id: string;
  meeting_id: string | null;
  task_suggestion_id: string | null;
  title: string;
  description: string | null;
  status: TaskStatus;
  priority: string;
  assignee_id: string | null;
  owner_id: string | null;
  created_by: string;
  due_date: string | null;
  is_manual: boolean;
  position: number;
  created_at: string;
  updated_at: string;
}

/**
 * Convert backend task response to frontend Task type
 */
function mapBackendTask(data: BackendTask): Task {
  return {
    id: data.id,
    projectId: data.project_id,
    title: data.title,
    description: data.description || "",
    deadline: data.due_date || new Date().toISOString(),
    assigneeIds: data.assignee_id ? [data.assignee_id] : [],
    transcriptReference: data.meeting_id || "",
    status: data.status,
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
    const response = await api.get<{
      items: BackendTask[];
      total: number;
    }>(`/frontend/tasks?${query}`);

    console.log("[TasksAPI] ✓ Tasks loaded:", response.items?.length || 0);
    return {
      tasks: (response.items || []).map(mapBackendTask),
      total: response.total || 0,
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
  const data = await api.get<BackendTask>(`/tasks/${taskId}`);
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
  const data = await api.post<BackendTask>("/tasks", input);
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
  const data = await api.patch<BackendTask>(`/tasks/${taskId}`, updates);
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
  actionItems: {
    title: string;
    description?: string;
    assignee?: string;
    deadline?: string;
  }[];
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
      actionItems: {
        title: string;
        description?: string;
        assignee?: string;
        deadline?: string;
      }[];
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
  actionItems: {
    title: string;
    description?: string;
    assignee?: string;
    deadline?: string;
  }[];
}> {
  console.log("[TranscriptAPI] Getting transcript status...", { transcriptId });

  const response = await api.get<{
    id: string;
    processingStatus: string;
    errorMessage?: string;
    summary?: string;
    actionItemIds: string[];
    actionItems: {
      title: string;
      description?: string;
      assignee?: string;
      deadline?: string;
    }[];
  }>(`/frontend/transcripts/${transcriptId}`);

  console.log(
    "[TranscriptAPI] ✓ Transcript status retrieved:",
    response.processingStatus,
  );

  return response;
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
}): Promise<{ success: boolean; taskIds: string[] }> {
  console.log("[PublishAPI] Publishing transcript to tasks");
  console.log("[PublishAPI] Request:", {
    projectId: input.projectId,
    transcriptId: input.transcriptId,
  });

  const requestBody = {
    projectId: input.projectId,
    transcriptId: input.transcriptId,
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

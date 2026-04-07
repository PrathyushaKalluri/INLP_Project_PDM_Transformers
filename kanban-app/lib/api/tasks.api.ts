import { z } from "zod";

import { apiClient, parseWithSchema } from "@/lib/api/client";
import type { Task } from "@/types";

const taskStatusSchema = z.enum(["todo", "in-progress", "completed"]);

const taskSchema = z.object({
  id: z.string(),
  projectId: z.string(),
  title: z.string(),
  description: z.string(),
  deadline: z.string(),
  assigneeIds: z.array(z.string()),
  transcriptReference: z.string(),
  status: taskStatusSchema,
});

const tasksSchema = z.array(taskSchema);

const createTaskPayloadSchema = z.object({
  projectId: z.string(),
  title: z.string().min(1),
  description: z.string().min(1),
  deadline: z.string().min(1),
  assigneeIds: z.array(z.string()),
  transcriptReference: z.string().min(1),
  status: taskStatusSchema,
});

const updateTaskPayloadSchema = z.object({
  title: z.string().min(1).optional(),
  description: z.string().min(1).optional(),
  deadline: z.string().min(1).optional(),
  assigneeIds: z.array(z.string()).optional(),
  transcriptReference: z.string().min(1).optional(),
  status: taskStatusSchema.optional(),
});

type CreateTaskPayload = z.infer<typeof createTaskPayloadSchema>;
type UpdateTaskPayload = z.infer<typeof updateTaskPayloadSchema>;

export async function getTasks(projectId: string): Promise<Task[]> {
  const response = await apiClient.get("/tasks", {
    params: { projectId },
  });
  return parseWithSchema(tasksSchema, response.data, "Invalid tasks response");
}

export async function createTask(payload: CreateTaskPayload): Promise<Task> {
  const body = createTaskPayloadSchema.parse(payload);
  const response = await apiClient.post("/tasks", body);
  return parseWithSchema(taskSchema, response.data, "Invalid task create response");
}

export async function updateTask(taskId: string, payload: UpdateTaskPayload): Promise<Task> {
  const body = updateTaskPayloadSchema.parse(payload);
  const response = await apiClient.patch(`/tasks/${taskId}`, body);
  return parseWithSchema(taskSchema, response.data, "Invalid task update response");
}

export async function deleteTask(taskId: string): Promise<void> {
  await apiClient.delete(`/tasks/${taskId}`);
}

import { z } from "zod";

import { apiClient, parseWithSchema } from "@/lib/api/client";
import type { Project } from "@/types";

const projectSchema = z.object({
  id: z.string(),
  name: z.string(),
  description: z.string(),
  participants: z.array(z.string()),
});

const projectsSchema = z.array(projectSchema);

const createProjectPayloadSchema = z.object({
  name: z.string().min(1),
  description: z.string().min(1),
});

const updateProjectPayloadSchema = z.object({
  name: z.string().min(1).optional(),
  description: z.string().min(1).optional(),
});

const participantsPayloadSchema = z.object({
  participantIds: z.array(z.string()),
});

type CreateProjectPayload = z.infer<typeof createProjectPayloadSchema>;
type UpdateProjectPayload = z.infer<typeof updateProjectPayloadSchema>;

export async function getProjects(): Promise<Project[]> {
  const response = await apiClient.get("/projects");
  return parseWithSchema(projectsSchema, response.data, "Invalid projects response");
}

export async function createProject(payload: CreateProjectPayload): Promise<Project> {
  const body = createProjectPayloadSchema.parse(payload);
  const response = await apiClient.post("/projects", body);
  return parseWithSchema(projectSchema, response.data, "Invalid project create response");
}

export async function updateProject(projectId: string, payload: UpdateProjectPayload): Promise<Project> {
  const body = updateProjectPayloadSchema.parse(payload);
  const response = await apiClient.patch(`/projects/${projectId}`, body);
  return parseWithSchema(projectSchema, response.data, "Invalid project update response");
}

export async function getProjectById(projectId: string): Promise<Project> {
  const response = await apiClient.get(`/projects/${projectId}`);
  return parseWithSchema(projectSchema, response.data, "Invalid project response");
}

export async function setProjectParticipants(projectId: string, participantIds: string[]): Promise<Project> {
  const body = participantsPayloadSchema.parse({ participantIds });
  const response = await apiClient.post(`/projects/${projectId}/participants`, body);
  return parseWithSchema(projectSchema, response.data, "Invalid project participants response");
}

import { z } from "zod";

import { apiClient, parseWithSchema } from "@/lib/api/client";
import type { Transcript } from "@/types";

const transcriptSchema = z.object({
  id: z.string(),
  projectId: z.string(),
  content: z.string(),
  summary: z.string(),
  createdAt: z.string(),
  actionItemIds: z.array(z.string()),
});

const transcriptsSchema = z.array(transcriptSchema);

const createTranscriptPayloadSchema = z.object({
  projectId: z.string(),
  content: z.string().min(1),
});

const publishPayloadSchema = z.object({
  projectId: z.string(),
  summary: z.string().min(1),
  actionItems: z.array(
    z.object({
      id: z.string(),
      title: z.string(),
      description: z.string(),
    })
  ),
});

type CreateTranscriptPayload = z.infer<typeof createTranscriptPayloadSchema>;
type PublishPayload = z.infer<typeof publishPayloadSchema>;

export async function createTranscript(payload: CreateTranscriptPayload): Promise<Transcript> {
  const body = createTranscriptPayloadSchema.parse(payload);
  const response = await apiClient.post("/transcripts", body);
  return parseWithSchema(transcriptSchema, response.data, "Invalid transcript create response");
}

export async function getTranscripts(projectId: string): Promise<Transcript[]> {
  const response = await apiClient.get("/transcripts", {
    params: { projectId },
  });
  return parseWithSchema(transcriptsSchema, response.data, "Invalid transcripts response");
}

export async function getTranscriptById(transcriptId: string): Promise<Transcript> {
  const response = await apiClient.get(`/transcripts/${transcriptId}`);
  return parseWithSchema(transcriptSchema, response.data, "Invalid transcript response");
}

export async function publishSummary(payload: PublishPayload) {
  const body = publishPayloadSchema.parse(payload);
  await apiClient.post("/publish", body);
}

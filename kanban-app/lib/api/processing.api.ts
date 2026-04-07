import { z } from "zod";

import { apiClient, parseWithSchema } from "@/lib/api/client";

const processingStepSchema = z.enum([
  "Analyzing transcript...",
  "Parsing transcript",
  "Extracting action items",
  "Generating summary",
]);

const startProcessingPayloadSchema = z.object({
  transcriptId: z.string(),
  projectId: z.string(),
});

const startProcessingResponseSchema = z.object({
  jobId: z.string(),
});

const processingStatusSchema = z.object({
  jobId: z.string(),
  status: z.enum(["pending", "running", "completed", "cancelled", "failed"]),
  currentStep: z.number().int().min(0).optional(),
  stepLabel: processingStepSchema.optional(),
  transcriptId: z.string().optional(),
  summary: z.string().optional(),
  actionItemIds: z.array(z.string()).optional(),
});

export type ProcessingStatus = z.infer<typeof processingStatusSchema>;

export async function startProcessing(payload: { transcriptId: string; projectId: string }) {
  const body = startProcessingPayloadSchema.parse(payload);
  const response = await apiClient.post("/processing/start", body);
  return parseWithSchema(startProcessingResponseSchema, response.data, "Invalid processing start response");
}

export async function getProcessingStatus(jobId: string): Promise<ProcessingStatus> {
  const response = await apiClient.get(`/processing/${jobId}/status`);
  return parseWithSchema(processingStatusSchema, response.data, "Invalid processing status response");
}

export async function cancelProcessing(jobId: string) {
  await apiClient.post(`/processing/${jobId}/cancel`);
}

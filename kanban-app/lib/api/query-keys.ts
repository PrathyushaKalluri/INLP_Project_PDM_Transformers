export const queryKeys = {
  authMe: ["auth", "me"] as const,
  projects: ["projects"] as const,
  project: (projectId: string) => ["projects", projectId] as const,
  tasks: (projectId: string) => ["tasks", projectId] as const,
  transcripts: (projectId: string) => ["transcripts", projectId] as const,
  transcript: (transcriptId: string) => ["transcript", transcriptId] as const,
  processingStatus: (jobId: string) => ["processing", jobId, "status"] as const,
  notifications: ["notifications"] as const,
};

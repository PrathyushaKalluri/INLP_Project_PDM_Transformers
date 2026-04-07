"use client";

import { useMemo, useState } from "react";
import { useRouter } from "next/navigation";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { useToast } from "@/components/ui/use-toast";
import { getProjects } from "@/lib/api/projects.api";
import { queryKeys } from "@/lib/api/query-keys";
import { getTasks, updateTask } from "@/lib/api/tasks.api";
import { getTranscriptById, publishSummary } from "@/lib/api/transcripts.api";
import { getErrorMessage } from "@/lib/utils";
import { useAppStore } from "@/store/useAppStore";

export function PublishEditor() {
  const router = useRouter();
  const { toast } = useToast();
  const queryClient = useQueryClient();

  const activeTranscriptId = useAppStore((state) => state.activeTranscriptId);

  const projectsQuery = useQuery({
    queryKey: queryKeys.projects,
    queryFn: getProjects,
  });

  const transcriptQuery = useQuery({
    queryKey: activeTranscriptId
      ? queryKeys.transcript(activeTranscriptId)
      : ["transcript", "none"],
    queryFn: () => getTranscriptById(activeTranscriptId ?? ""),
    enabled: Boolean(activeTranscriptId),
  });

  const transcript = transcriptQuery.data;

  const tasksQuery = useQuery({
    queryKey: transcript?.projectId
      ? queryKeys.tasks(transcript.projectId)
      : ["tasks", "none"],
    queryFn: () => getTasks(transcript?.projectId ?? ""),
    enabled: Boolean(transcript?.projectId),
  });

  const projects = useMemo(() => projectsQuery.data ?? [], [projectsQuery.data]);
  const tasks = useMemo(() => tasksQuery.data ?? [], [tasksQuery.data]);

  const [summaryDrafts, setSummaryDrafts] = useState<Record<string, string>>({});
  const [meetingTitle, setMeetingTitle] = useState("Weekly Sync");
  const [meetingDate, setMeetingDate] = useState(new Date().toISOString().slice(0, 10));

  const summary = transcript
    ? (summaryDrafts[transcript.id] ?? transcript.summary)
    : "";

  const relatedTasks = useMemo(() => {
    if (!transcript) {
      return [];
    }

    return tasks.filter((task) => transcript.actionItemIds.includes(task.id));
  }, [tasks, transcript]);

  const currentProject = useMemo(
    () => projects.find((project) => project.id === transcript?.projectId),
    [projects, transcript?.projectId]
  );

  const updateTaskMutation = useMutation({
    mutationFn: ({
      taskId,
      payload,
    }: {
      taskId: string;
      payload: { title?: string; description?: string };
    }) => updateTask(taskId, payload),
    onSuccess: () => {
      if (transcript?.projectId) {
        queryClient.invalidateQueries({
          queryKey: queryKeys.tasks(transcript.projectId),
        });
      }
    },
    onError: (error) => {
      toast({
        title: "Failed to update task",
        description: getErrorMessage(error),
      });
    },
  });

  const publishMutation = useMutation({
    mutationFn: publishSummary,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.notifications });
      toast({
        title: "Published",
        description: `Published summary for ${currentProject?.name ?? "project"}.`,
      });
    },
    onError: (error) => {
      toast({
        title: "Publish failed",
        description: getErrorMessage(error),
      });
    },
  });

  const publish = async () => {
    if (!transcript) {
      return;
    }

    await publishMutation.mutateAsync({
      projectId: transcript.projectId,
      summary,
      actionItems: relatedTasks.map((task) => ({
        id: task.id,
        title: task.title,
        description: task.description,
      })),
    });
  };

  if (transcriptQuery.isLoading) {
    return (
      <Card>
        <CardContent className="p-4">
          <p className="text-sm text-text-secondary">Loading transcript...</p>
        </CardContent>
      </Card>
    );
  }

  if (!transcript) {
    return (
      <Card>
        <CardContent className="p-4">
          <p className="text-sm text-text-secondary">
            No transcript found. Upload a transcript to continue.
          </p>
        </CardContent>
      </Card>
    );
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between gap-2">
        <div>
          <h2 className="text-2xl font-semibold text-text-primary">Publish Review</h2>
          <p className="text-sm text-text-secondary">Finalize summary and editable action items.</p>
        </div>
        <Button onClick={publish} disabled={publishMutation.isPending}>
          Publish
        </Button>
      </div>

      <div className="grid gap-4 xl:grid-cols-[1fr_1fr]">
        <Card>
          <CardHeader>
            <CardTitle className="text-xl font-medium">Meeting summary</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="grid gap-2">
              <Label htmlFor="meeting-title">Meeting title</Label>
              <Input
                id="meeting-title"
                value={meetingTitle}
                onChange={(event) => setMeetingTitle(event.target.value)}
              />
            </div>

            <div className="grid gap-2">
              <Label htmlFor="meeting-date">Meeting date</Label>
              <Input
                id="meeting-date"
                type="date"
                value={meetingDate}
                onChange={(event) => setMeetingDate(event.target.value)}
              />
            </div>

            <div className="grid gap-2">
              <Label htmlFor="meeting-summary">Summary</Label>
              <Textarea
                id="meeting-summary"
                className="min-h-[15rem]"
                value={summary}
                onChange={(event) => {
                  if (!transcript) {
                    return;
                  }
                  setSummaryDrafts((prev) => ({
                    ...prev,
                    [transcript.id]: event.target.value,
                  }));
                }}
              />
            </div>

            <Button variant="secondary" onClick={() => router.push("/dashboard/upload")}>
              Edit meeting info
            </Button>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="text-xl font-medium">Editable action items</CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            {relatedTasks.length === 0 ? (
              <p className="rounded-xl border border-dashed border-border p-3 text-sm text-text-secondary">
                No action items generated yet.
              </p>
            ) : (
              relatedTasks.map((task) => (
                <div key={task.id} className="rounded-xl border border-border p-3">
                  <div className="grid gap-2">
                    <Label htmlFor={`title-${task.id}`}>Task title</Label>
                    <Input
                      id={`title-${task.id}`}
                      value={task.title}
                      onChange={(event) =>
                        updateTaskMutation.mutate({
                          taskId: task.id,
                          payload: { title: event.target.value },
                        })
                      }
                    />
                  </div>
                  <div className="mt-2 grid gap-2">
                    <Label htmlFor={`description-${task.id}`}>Description</Label>
                    <Textarea
                      id={`description-${task.id}`}
                      value={task.description}
                      onChange={(event) =>
                        updateTaskMutation.mutate({
                          taskId: task.id,
                          payload: { description: event.target.value },
                        })
                      }
                    />
                  </div>
                </div>
              ))
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  );
}

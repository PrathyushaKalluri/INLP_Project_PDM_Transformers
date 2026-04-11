"use client";

import { useEffect, useMemo, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { useToast } from "@/components/ui/use-toast";
import {
  type TranscriptActionItem,
  listTasks,
  listTranscriptsApi,
  publishActionItemsApi,
  saveTranscriptEditsApi,
} from "@/lib/tasks";
import { listTeamMembersApi } from "@/lib/teams";
import { useAppStore } from "@/store/useAppStore";
import type { User } from "@/types";

type ApiError = Error & { status?: number };

const isMethodNotAllowed = (error: unknown): boolean => {
  const apiError = error as ApiError;
  return apiError?.status === 405;
};

export function PublishEditor() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const { toast } = useToast();
  const transcriptQueryId = searchParams.get("transcriptId");

  const projects = useAppStore((state) => state.projects);
  const selectedProject = useAppStore((state) => state.selectedProject);
  const activeTranscriptId = useAppStore((state) => state.activeTranscriptId);
  const transcripts = useAppStore((state) => state.transcripts);
  const tasks = useAppStore((state) => state.tasks);
  const addNotification = useAppStore((state) => state.addNotification);
  const setSelectedProject = useAppStore((state) => state.setSelectedProject);
  const setTranscripts = useAppStore((state) => state.setTranscripts);
  const setActiveTranscript = useAppStore((state) => state.setActiveTranscript);
  const setTasks = useAppStore((state) => state.setTasks);

  const [users, setUsers] = useState<User[]>([]);
  const transcript = useMemo(
    () =>
      transcripts.find((item) => item.id === activeTranscriptId) ??
      transcripts[0],
    [transcripts, activeTranscriptId],
  );

  const [summary, setSummary] = useState("");
  const [meetingTitle, setMeetingTitle] = useState("Weekly Sync");
  const [meetingDate, setMeetingDate] = useState(
    new Date().toISOString().slice(0, 10),
  );
  const [editableItems, setEditableItems] = useState<TranscriptActionItem[]>(
    [],
  );
  const [isSavingEdits, setIsSavingEdits] = useState(false);
  const [isPublishing, setIsPublishing] = useState(false);

  useEffect(() => {
    if (!selectedProject && projects.length > 0) {
      setSelectedProject(projects[0].id);
    }
  }, [selectedProject, projects, setSelectedProject]);

  const currentProject = projects.find(
    (project) => project.id === selectedProject,
  );

  useEffect(() => {
    if (!selectedProject) return;

    let cancelled = false;

    const loadTranscripts = async () => {
      try {
        const [members, items] = await Promise.all([
          currentProject?.teamId
            ? listTeamMembersApi(currentProject.teamId)
            : Promise.resolve([]),
          listTranscriptsApi(selectedProject),
        ]);

        if (cancelled) return;

        setUsers(
          members.map((m) => ({
            id: m.user_id,
            name: m.full_name,
            email: m.email,
            role: "member",
            avatar: m.full_name
              .split(" ")
              .map((part) => part[0])
              .join("")
              .slice(0, 2)
              .toUpperCase(),
          })),
        );
        setTranscripts(items);

        if (
          transcriptQueryId &&
          items.some((item) => item.id === transcriptQueryId)
        ) {
          setActiveTranscript(transcriptQueryId);
          return;
        }

        if (
          activeTranscriptId &&
          items.some((item) => item.id === activeTranscriptId)
        ) {
          return;
        }

        setActiveTranscript(items[0]?.id ?? null);
      } catch (error) {
        console.error("[PublishEditor] Failed to load transcripts:", error);
      }
    };

    loadTranscripts();
    return () => {
      cancelled = true;
    };
  }, [
    selectedProject,
    currentProject?.teamId,
    transcriptQueryId,
    activeTranscriptId,
    setActiveTranscript,
    setTranscripts,
  ]);

  useEffect(() => {
    setSummary(transcript?.summary ?? "");
    setEditableItems(transcript?.actionItems ?? []);
  }, [transcript?.id, transcript?.summary, transcript?.actionItems]);

  const saveEdits = async () => {
    if (!transcript) return;

    setIsSavingEdits(true);
    try {
      const updated = await saveTranscriptEditsApi({
        transcriptId: transcript.id,
        summary,
        actionItems: editableItems,
      });

      setTranscripts(
        transcripts.map((entry) =>
          entry.id === updated.id
            ? {
                ...entry,
                summary: updated.summary,
                actionItems: updated.actionItems || [],
              }
            : entry,
        ),
      );
      syncKanbanTasksFromEdits(updated.id, editableItems);

      toast({
        title: "Edits Saved",
        description: "Meeting summary edits were saved.",
      });
    } catch (error) {
      if (isMethodNotAllowed(error)) {
        setTranscripts(
          transcripts.map((entry) =>
            entry.id === transcript.id
              ? {
                  ...entry,
                  summary,
                  actionItems: editableItems,
                }
              : entry,
          ),
        );
        syncKanbanTasksFromEdits(transcript.id, editableItems);

        toast({
          title: "Saved Locally",
          description:
            "Your backend on port 8000 does not support saving transcript edits yet (405). Edits are kept locally and will still be used when publishing.",
        });
        return;
      }

      const errorMsg =
        error instanceof Error ? error.message : "Failed to save edits";
      toast({
        title: "Save Failed",
        description: errorMsg,
      });
    } finally {
      setIsSavingEdits(false);
    }
  };

  const publish = async () => {
    if (!transcript || !currentProject) {
      console.warn("[PublishEditor] Missing transcript or project");
      return;
    }

    setIsPublishing(true);
    try {
      console.log("[PublishEditor] Publishing transcript...", {
        projectId: currentProject.id,
        transcriptId: transcript.id,
      });

      try {
        await saveTranscriptEditsApi({
          transcriptId: transcript.id,
          summary,
          actionItems: editableItems,
        });
      } catch (error) {
        if (!isMethodNotAllowed(error)) {
          throw error;
        }

        toast({
          title: "Publish Using Local Edits",
          description:
            "Backend save endpoint returned 405, so publishing will continue with your local edited action items.",
        });
      }

      const result = await publishActionItemsApi({
        projectId: currentProject.id,
        transcriptId: transcript.id,
        actionItems: editableItems.filter(
          (item) => (item.title ?? "").trim().length > 0,
        ),
      });

      console.log("[PublishEditor] Publish succeeded:", result);

      if (result.success) {
        // Ensure kanban opens on the same project where tasks were published.
        setSelectedProject(currentProject.id);

        // Preload latest tasks so users see published items immediately after redirect.
        const refreshed = await listTasks({ projectId: currentProject.id });
        setTasks(refreshed.tasks);

        addNotification({
          message: `Published ${result.taskIds.length} action items for ${currentProject.name}.`,
          type: "success",
        });
        toast({
          title: "Published",
          description: `Successfully published ${result.taskIds.length} action items to the kanban board.`,
        });

        // Redirect to kanban board to see the published tasks
        setTimeout(() => {
          router.push("/dashboard/kanban");
        }, 1000);
      }
    } catch (error) {
      const errorMsg =
        error instanceof Error
          ? error.message
          : "Failed to publish action items";
      console.error("[PublishEditor] Publish error:", error);
      addNotification({
        message: `Error publishing: ${errorMsg}`,
        type: "warning",
      });
      toast({
        title: "Publish Failed",
        description: errorMsg,
      });
    } finally {
      setIsPublishing(false);
    }
  };

  const updateEditableItem = (
    index: number,
    updates: Partial<TranscriptActionItem>,
  ) => {
    setEditableItems((prev) =>
      prev.map((item, i) => (i === index ? { ...item, ...updates } : item)),
    );
  };

  const syncKanbanTasksFromEdits = (
    transcriptId: string,
    actionItems: TranscriptActionItem[],
  ) => {
    const transcriptTasks = tasks.filter(
      (task) => task.transcriptReference === transcriptId,
    );

    if (transcriptTasks.length === 0) {
      return;
    }

    const taskIndexById = new Map(
      transcriptTasks.map((task, index) => [task.id, index]),
    );

    setTasks(
      tasks.map((task) => {
        if (task.transcriptReference !== transcriptId) {
          return task;
        }

        const taskIndex = taskIndexById.get(task.id) ?? -1;
        const actionItem = actionItems[taskIndex];

        if (!actionItem) {
          return task;
        }

        return {
          ...task,
          title: actionItem.title?.trim() || task.title,
          description: actionItem.description?.trim() ?? task.description,
          deadline: actionItem.deadline ?? task.deadline,
          assigneeIds: actionItem.assignee ? [actionItem.assignee] : [],
        };
      }),
    );
  };

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
          <h2 className="text-2xl font-semibold text-text-primary">
            Publish Review
          </h2>
          <p className="text-sm text-text-secondary">
            Finalize summary and editable action items.
          </p>
        </div>
        <div className="flex items-center gap-2">
          <div className="grid gap-1">
            <Label htmlFor="transcript-select" className="text-xs">
              Meeting summary
            </Label>
            <select
              id="transcript-select"
              value={transcript.id}
              onChange={(event) => setActiveTranscript(event.target.value)}
              className="rounded-md border border-border bg-card px-3 py-2 text-sm text-text-primary min-w-64"
            >
              {transcripts.map((item) => (
                <option key={item.id} value={item.id}>
                  {new Date(item.createdAt).toLocaleString()} -{" "}
                  {item.id.slice(0, 8)}
                </option>
              ))}
            </select>
          </div>
          <Button
            variant="secondary"
            onClick={saveEdits}
            disabled={isSavingEdits}
          >
            {isSavingEdits ? "Saving..." : "Save Edits"}
          </Button>
          <Button onClick={publish} disabled={isPublishing}>
            {isPublishing ? "Publishing..." : "Publish"}
          </Button>
        </div>
      </div>

      <div className="grid gap-4 xl:grid-cols-[1fr_1fr]">
        <Card>
          <CardHeader>
            <CardTitle className="text-xl font-medium">
              Meeting summary
            </CardTitle>
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
                onChange={(event) => setSummary(event.target.value)}
              />
            </div>

            <Button
              variant="secondary"
              onClick={() => router.push("/dashboard/upload")}
            >
              Edit meeting info
            </Button>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="text-xl font-medium">
              Editable action items
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            {!editableItems.length ? (
              <p className="rounded-xl border border-dashed border-border p-3 text-sm text-text-secondary">
                No action items generated yet.
              </p>
            ) : (
              editableItems.map((item, idx) => (
                <div
                  key={`${transcript.id}-item-${idx}`}
                  className="rounded-xl border border-border p-3"
                >
                  <div className="grid gap-2">
                    <Label htmlFor={`title-${idx}`}>Task title</Label>
                    <Input
                      id={`title-${idx}`}
                      value={item.title ?? ""}
                      onChange={(event) =>
                        updateEditableItem(idx, { title: event.target.value })
                      }
                    />
                  </div>
                  <div className="mt-2 grid gap-2">
                    <Label htmlFor={`description-${idx}`}>Description</Label>
                    <Textarea
                      id={`description-${idx}`}
                      value={item.description ?? ""}
                      onChange={(event) =>
                        updateEditableItem(idx, {
                          description: event.target.value,
                        })
                      }
                    />
                  </div>
                  <div className="mt-2 grid gap-2 md:grid-cols-2">
                    <div className="grid gap-2">
                      <Label htmlFor={`deadline-${idx}`}>Deadline</Label>
                      <Input
                        id={`deadline-${idx}`}
                        type="date"
                        value={item.deadline ?? ""}
                        onChange={(event) =>
                          updateEditableItem(idx, {
                            deadline: event.target.value,
                          })
                        }
                      />
                    </div>
                    <div className="grid gap-2">
                      <Label htmlFor={`assignee-${idx}`}>Assignee</Label>
                      <select
                        id={`assignee-${idx}`}
                        value={item.assignee ?? ""}
                        onChange={(event) =>
                          updateEditableItem(idx, {
                            assignee: event.target.value,
                          })
                        }
                        className="rounded-md border border-border bg-card px-3 py-2 text-sm text-text-primary"
                      >
                        <option value="">Unassigned</option>
                        {users.map((user) => (
                          <option key={user.id} value={user.id}>
                            {user.name}
                          </option>
                        ))}
                      </select>
                    </div>
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

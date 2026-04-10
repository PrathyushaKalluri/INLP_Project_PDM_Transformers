"use client";

import { useEffect, useMemo, useState } from "react";
import { useRouter } from "next/navigation";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { useToast } from "@/components/ui/use-toast";
import { listTasks } from "@/lib/tasks";
import { useAppStore } from "@/store/useAppStore";
import { publishActionItemsApi } from "@/lib/tasks";

export function PublishEditor() {
  const router = useRouter();
  const { toast } = useToast();

  const projects = useAppStore((state) => state.projects);
  const activeTranscriptId = useAppStore((state) => state.activeTranscriptId);
  const transcripts = useAppStore((state) => state.transcripts);
  const addNotification = useAppStore((state) => state.addNotification);
  const setSelectedProject = useAppStore((state) => state.setSelectedProject);
  const setTasks = useAppStore((state) => state.setTasks);

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
  const [isPublishing, setIsPublishing] = useState(false);

  useEffect(() => {
    setSummary(transcript?.summary ?? "");
  }, [transcript?.id, transcript?.summary]);

  const currentProject = projects.find(
    (project) => project.id === transcript?.projectId,
  );

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

      // SIMPLIFIED API CALL - Backend fetches action items from transcript
      // No need to send actionItems from frontend
      const result = await publishActionItemsApi({
        projectId: currentProject.id,
        transcriptId: transcript.id,
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
        <Button onClick={publish} disabled={isPublishing}>
          {isPublishing ? "Publishing..." : "Publish"}
        </Button>
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
            {!transcript.actionItems?.length ? (
              <p className="rounded-xl border border-dashed border-border p-3 text-sm text-text-secondary">
                No action items generated yet.
              </p>
            ) : (
              transcript.actionItems.map((item, idx) => (
                <div
                  key={`${transcript.id}-item-${idx}`}
                  className="rounded-xl border border-border p-3"
                >
                  <div className="grid gap-2">
                    <Label htmlFor={`title-${idx}`}>Task title</Label>
                    <Input
                      id={`title-${idx}`}
                      value={item.title ?? ""}
                      readOnly
                    />
                  </div>
                  <div className="mt-2 grid gap-2">
                    <Label htmlFor={`description-${idx}`}>Description</Label>
                    <Textarea
                      id={`description-${idx}`}
                      value={item.description ?? ""}
                      readOnly
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

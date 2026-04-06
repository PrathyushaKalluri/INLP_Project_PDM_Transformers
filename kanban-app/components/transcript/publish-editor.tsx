"use client";

import { useMemo, useState } from "react";
import { useRouter } from "next/navigation";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { useToast } from "@/components/ui/use-toast";
import { useAppStore } from "@/store/useAppStore";

export function PublishEditor() {
  const router = useRouter();
  const { toast } = useToast();

  const projects = useAppStore((state) => state.projects);
  const activeTranscriptId = useAppStore((state) => state.activeTranscriptId);
  const transcripts = useAppStore((state) => state.transcripts);
  const tasks = useAppStore((state) => state.tasks);
  const updateTask = useAppStore((state) => state.updateTask);
  const updateTranscript = useAppStore((state) => state.updateTranscript);
  const addNotification = useAppStore((state) => state.addNotification);

  const transcript = useMemo(
    () => transcripts.find((item) => item.id === activeTranscriptId) ?? transcripts[0],
    [transcripts, activeTranscriptId]
  );

  const [summary, setSummary] = useState(transcript?.summary ?? "");
  const [meetingTitle, setMeetingTitle] = useState("Weekly Sync");
  const [meetingDate, setMeetingDate] = useState(new Date().toISOString().slice(0, 10));

  const relatedTasks = useMemo(() => {
    if (!transcript) {
      return [];
    }

    return tasks.filter((task) => transcript.actionItemIds.includes(task.id));
  }, [tasks, transcript]);

  const currentProject = projects.find((project) => project.id === transcript?.projectId);

  const publish = () => {
    if (!transcript) {
      return;
    }

    updateTranscript(transcript.id, { summary });
    addNotification({
      message: `Published summary for ${currentProject?.name ?? "project"}.`,
      type: "success",
    });
    toast({
      title: "Published",
      description: "Meeting summary and action items were published.",
    });
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
          <h2 className="text-2xl font-semibold text-text-primary">Publish Review</h2>
          <p className="text-sm text-text-secondary">Finalize summary and editable action items.</p>
        </div>
        <Button onClick={publish}>Publish</Button>
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
                onChange={(event) => setSummary(event.target.value)}
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
                        updateTask(task.id, { title: event.target.value })
                      }
                    />
                  </div>
                  <div className="mt-2 grid gap-2">
                    <Label htmlFor={`description-${task.id}`}>Description</Label>
                    <Textarea
                      id={`description-${task.id}`}
                      value={task.description}
                      onChange={(event) =>
                        updateTask(task.id, { description: event.target.value })
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

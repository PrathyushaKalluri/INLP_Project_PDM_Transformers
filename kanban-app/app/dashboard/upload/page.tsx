"use client";

import { useMemo, useState } from "react";
import { useRouter } from "next/navigation";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { ArrowLeft } from "lucide-react";

import { SectionHeading } from "@/components/shared/section-heading";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Label } from "@/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Textarea } from "@/components/ui/textarea";
import { getProjects } from "@/lib/api/projects.api";
import { startProcessing as startProcessingApi } from "@/lib/api/processing.api";
import { queryKeys } from "@/lib/api/query-keys";
import { createTranscript } from "@/lib/api/transcripts.api";
import { getErrorMessage } from "@/lib/utils";
import { useToast } from "@/components/ui/use-toast";
import { useAppStore } from "@/store/useAppStore";

export default function UploadPage() {
  const router = useRouter();
  const queryClient = useQueryClient();
  const { toast } = useToast();
  const selectedProject = useAppStore((state) => state.selectedProject);
  const setSelectedProject = useAppStore((state) => state.setSelectedProject);
  const startProcessing = useAppStore((state) => state.startProcessing);
  const resetProcessing = useAppStore((state) => state.resetProcessing);

  const [transcript, setTranscript] = useState("");

  const projectsQuery = useQuery({
    queryKey: queryKeys.projects,
    queryFn: getProjects,
  });

  const projects = projectsQuery.data ?? [];

  const uploadMutation = useMutation({
    mutationFn: async ({ projectId, content }: { projectId: string; content: string }) => {
      const createdTranscript = await createTranscript({
        projectId,
        content,
      });
      const started = await startProcessingApi({
        transcriptId: createdTranscript.id,
        projectId,
      });

      return {
        transcript: createdTranscript,
        jobId: started.jobId,
      };
    },
    onSuccess: ({ transcript: createdTranscript, jobId }) => {
      queryClient.invalidateQueries({ queryKey: queryKeys.transcripts(createdTranscript.projectId) });
      useAppStore.getState().setActiveTranscript(createdTranscript.id);
      resetProcessing();
      startProcessing(jobId, createdTranscript.id);
      router.push("/dashboard/processing");
    },
    onError: (error) => {
      toast({
        title: "Transcript upload failed",
        description: getErrorMessage(error),
      });
    },
  });

  const canSubmit = useMemo(
    () => Boolean(selectedProject) && transcript.trim().length > 20,
    [selectedProject, transcript]
  );

  const handleSubmit = async () => {
    if (!selectedProject || !canSubmit) {
      return;
    }

    await uploadMutation.mutateAsync({
      projectId: selectedProject,
      content: transcript.trim(),
    });
  };

  return (
    <div className="space-y-4">
      <SectionHeading
        title="Upload Transcript"
        subtitle="Paste meeting notes or transcript text to extract action items."
        action={
          <div className="min-w-60">
            <Select value={selectedProject ?? undefined} onValueChange={setSelectedProject}>
              <SelectTrigger>
                <SelectValue placeholder="Select project" />
              </SelectTrigger>
              <SelectContent>
                {projects.map((project) => (
                  <SelectItem key={project.id} value={project.id}>
                    {project.name}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
        }
      />

      <Card>
        <CardHeader>
          <CardTitle className="text-xl font-medium">Meeting Transcript</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="grid gap-2">
            <Label htmlFor="transcript-input">Transcript text</Label>
            <Textarea
              id="transcript-input"
              className="min-h-[20rem]"
              placeholder="Paste your full meeting transcript here..."
              value={transcript}
              onChange={(event) => setTranscript(event.target.value)}
            />
          </div>

          <div className="flex flex-wrap items-center justify-between gap-2">
            <Button variant="ghost" onClick={() => router.push("/dashboard/kanban")}> 
              <ArrowLeft className="h-4 w-4" />
              Back
            </Button>

            <Button onClick={handleSubmit} disabled={!canSubmit || uploadMutation.isPending}>
              Extract Action Items
            </Button>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}

"use client";

import { useMemo, useState } from "react";
import { useRouter } from "next/navigation";

import { ArrowLeft } from "lucide-react";

import { SectionHeading } from "@/components/shared/section-heading";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { useAppStore } from "@/store/useAppStore";

export default function UploadPage() {
  const router = useRouter();
  const selectedProject = useAppStore((state) => state.selectedProject);
  const startProcessing = useAppStore((state) => state.startProcessing);
  const resetProcessing = useAppStore((state) => state.resetProcessing);

  const [transcript, setTranscript] = useState("");

  const canSubmit = useMemo(
    () => Boolean(selectedProject) && transcript.trim().length > 20,
    [selectedProject, transcript],
  );

  const handleSubmit = async () => {
    if (!selectedProject || !canSubmit) {
      return;
    }

    try {
      resetProcessing();
      await startProcessing(selectedProject, transcript.trim());
      router.push("/dashboard/processing");
    } catch (error) {
      console.error("Failed to start processing:", error);
      // Handle error - could show a toast notification
    }
  };

  return (
    <div className="space-y-4">
      <SectionHeading
        title="Upload Transcript"
        subtitle="Paste meeting notes or transcript text to extract action items."
      />

      <Card>
        <CardHeader>
          <CardTitle className="text-xl font-medium">
            Meeting Transcript
          </CardTitle>
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
            <Button
              variant="ghost"
              onClick={() => router.push("/dashboard/kanban")}
            >
              <ArrowLeft className="h-4 w-4" />
              Back
            </Button>

            <Button onClick={handleSubmit} disabled={!canSubmit}>
              Extract Action Items
            </Button>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}

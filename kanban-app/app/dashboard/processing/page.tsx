"use client";

import { useEffect, useRef } from "react";
import { useRouter } from "next/navigation";

import { Button } from "@/components/ui/button";
import { ProcessingView } from "@/components/transcript/processing-view";
import { useAppStore } from "@/store/useAppStore";
import { PROCESSING_STEPS } from "@/types";
import { getTranscriptStatusApi } from "@/lib/tasks";

export default function ProcessingPage() {
  const router = useRouter();
  const processingState = useAppStore((state) => state.processingState);
  const pendingTranscript = useAppStore((state) => state.pendingTranscript);
  const advanceProcessing = useAppStore((state) => state.advanceProcessing);
  const completeProcessing = useAppStore((state) => state.completeProcessing);
  const cancelProcessing = useAppStore((state) => state.cancelProcessing);
  const hasCompletedRef = useRef(false);
  const transcriptId = pendingTranscript?.transcriptId;

  useEffect(() => {
    if (!processingState.isProcessing) {
      if (processingState.cancelled) {
        router.replace("/dashboard/processing/cancelled");
      } else {
        router.replace("/dashboard/publish");
      }
      return;
    }

    // Wait until store has transcript id from upload completion.
    if (!transcriptId) {
      return;
    }

    const pollStatus = async () => {
      try {
        const status = await getTranscriptStatusApi(transcriptId);

        if (status.processingStatus === "COMPLETED") {
          if (hasCompletedRef.current) {
            return;
          }
          hasCompletedRef.current = true;
          await completeProcessing();
          router.replace("/dashboard/publish");
        } else if (status.processingStatus === "CANCELLED") {
          router.replace("/dashboard/processing/cancelled");
        } else if (status.processingStatus === "FAILED") {
          console.error(
            "[Processing] Transcript processing failed:",
            status.errorMessage,
          );
          const reason = encodeURIComponent(
            status.errorMessage || "Transcript processing failed",
          );
          router.replace(`/dashboard/processing/failed?reason=${reason}`);
        } else if (processingState.currentStep < PROCESSING_STEPS.length - 2) {
          // Keep visual progress moving while backend remains in PENDING/PROCESSING.
          advanceProcessing();
        }
      } catch (error) {
        console.error("[Processing] Failed to check transcript status:", error);
      }
    };

    pollStatus();
    const interval = setInterval(pollStatus, 4000);

    return () => clearInterval(interval);
  }, [
    processingState.isProcessing,
    processingState.cancelled,
    processingState.currentStep,
    transcriptId,
    router,
    completeProcessing,
    advanceProcessing,
  ]);

  return (
    <div className="flex min-h-[calc(100vh-10rem)] items-center justify-center">
      <div className="space-y-4">
        <ProcessingView currentStep={processingState.currentStep} />
        <div className="flex justify-end">
          <Button variant="destructive" onClick={cancelProcessing}>
            Cancel
          </Button>
        </div>
      </div>
    </div>
  );
}

"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";

import { Button } from "@/components/ui/button";
import { ProcessingView } from "@/components/transcript/processing-view";
import {
  cancelProcessing as cancelProcessingApi,
  getProcessingStatus,
} from "@/lib/api/processing.api";
import { queryKeys } from "@/lib/api/query-keys";
import { getTranscriptById } from "@/lib/api/transcripts.api";
import { getErrorMessage } from "@/lib/utils";
import { useToast } from "@/components/ui/use-toast";
import { useAppStore } from "@/store/useAppStore";
import { PROCESSING_STEPS } from "@/types";

export default function ProcessingPage() {
  const router = useRouter();
  const queryClient = useQueryClient();
  const { toast } = useToast();
  const processingState = useAppStore((state) => state.processingState);
  const setProcessingStep = useAppStore((state) => state.setProcessingStep);
  const completeProcessing = useAppStore((state) => state.completeProcessing);
  const cancelProcessingLocal = useAppStore((state) => state.cancelProcessingLocal);
  const failProcessing = useAppStore((state) => state.failProcessing);
  const setActiveTranscript = useAppStore((state) => state.setActiveTranscript);

  const processingQuery = useQuery({
    queryKey: processingState.jobId
      ? queryKeys.processingStatus(processingState.jobId)
      : ["processing", "idle"],
    queryFn: () => getProcessingStatus(processingState.jobId ?? ""),
    enabled: Boolean(processingState.jobId) && processingState.isProcessing,
    refetchInterval: (query) => {
      const status = query.state.data?.status;
      if (!status || status === "running" || status === "pending") {
        return 2000;
      }
      return false;
    },
  });

  const cancelMutation = useMutation({
    mutationFn: async () => {
      if (!processingState.jobId) {
        return;
      }
      await cancelProcessingApi(processingState.jobId);
    },
    onSuccess: () => {
      cancelProcessingLocal();
    },
    onError: (error) => {
      toast({
        title: "Failed to cancel processing",
        description: getErrorMessage(error),
      });
    },
  });

  useEffect(() => {
    if (!processingState.jobId && !processingState.isProcessing) {
      router.replace("/dashboard/upload");
      return;
    }

    if (!processingState.isProcessing) {
      if (processingState.cancelled) {
        router.replace("/dashboard/processing/cancelled");
      } else {
        router.replace("/dashboard/publish");
      }
      return;
    }

    if (!processingQuery.data) {
      return;
    }

    const status = processingQuery.data.status;
    const nextStep =
      typeof processingQuery.data.currentStep === "number"
        ? Math.min(processingQuery.data.currentStep, PROCESSING_STEPS.length - 1)
        : processingState.currentStep;

    setProcessingStep(nextStep);

    if (status === "cancelled") {
      cancelProcessingLocal();
      return;
    }

    if (status === "completed") {
      const transcriptId = processingQuery.data.transcriptId ?? processingState.transcriptId;
      if (transcriptId) {
        setActiveTranscript(transcriptId);
        queryClient.invalidateQueries({ queryKey: queryKeys.transcript(transcriptId) });
        queryClient.invalidateQueries({ queryKey: ["transcripts"] });
        queryClient.invalidateQueries({ queryKey: ["tasks"] });
      }
      completeProcessing();
      return;
    }

    if (status === "failed") {
      failProcessing("Processing failed. Please retry from upload.");
      toast({
        title: "Processing failed",
        description: "Please retry the transcript processing.",
      });
      router.replace("/dashboard/upload");
      return;
    }
  }, [
    cancelProcessingLocal,
    completeProcessing,
    failProcessing,
    processingQuery.data,
    processingState.cancelled,
    processingState.currentStep,
    processingState.isProcessing,
    processingState.jobId,
    processingState.transcriptId,
    queryClient,
    router,
    setActiveTranscript,
    setProcessingStep,
    toast,
  ]);

  useQuery({
    queryKey: processingState.transcriptId
      ? queryKeys.transcript(processingState.transcriptId)
      : ["transcript", "idle"],
    queryFn: () => getTranscriptById(processingState.transcriptId ?? ""),
    enabled: Boolean(processingState.transcriptId) && !processingState.isProcessing,
  });

  return (
    <div className="flex min-h-[calc(100vh-10rem)] items-center justify-center">
      <div className="space-y-4">
        <ProcessingView currentStep={processingState.currentStep} />
        <div className="flex justify-end">
          <Button
            variant="destructive"
            onClick={() => cancelMutation.mutate()}
            disabled={cancelMutation.isPending}
          >
            Cancel
          </Button>
        </div>
      </div>
    </div>
  );
}

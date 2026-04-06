"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";

import { Button } from "@/components/ui/button";
import { ProcessingView } from "@/components/transcript/processing-view";
import { useAppStore } from "@/store/useAppStore";
import { PROCESSING_STEPS } from "@/types";

export default function ProcessingPage() {
  const router = useRouter();
  const processingState = useAppStore((state) => state.processingState);
  const advanceProcessing = useAppStore((state) => state.advanceProcessing);
  const completeProcessing = useAppStore((state) => state.completeProcessing);
  const cancelProcessing = useAppStore((state) => state.cancelProcessing);

  useEffect(() => {
    if (!processingState.isProcessing) {
      if (processingState.cancelled) {
        router.replace("/dashboard/processing/cancelled");
      } else {
        router.replace("/dashboard/publish");
      }
      return;
    }

    const interval = setInterval(() => {
      const latest = useAppStore.getState().processingState;
      if (!latest.isProcessing) {
        clearInterval(interval);
        return;
      }

      if (latest.currentStep >= PROCESSING_STEPS.length - 1) {
        useAppStore.getState().completeProcessing();
        return;
      }

      useAppStore.getState().advanceProcessing();
    }, 1200);

    return () => clearInterval(interval);
  }, [
    processingState.isProcessing,
    processingState.cancelled,
    router,
    advanceProcessing,
    completeProcessing,
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

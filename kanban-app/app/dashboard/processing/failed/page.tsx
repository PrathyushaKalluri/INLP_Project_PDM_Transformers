"use client";

import { useEffect } from "react";
import { useRouter, useSearchParams } from "next/navigation";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { useAppStore } from "@/store/useAppStore";

export default function ProcessingFailedPage() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const resetProcessing = useAppStore((state) => state.resetProcessing);

  const reason =
    searchParams.get("reason") ||
    "Transcript processing failed. Please try again.";

  useEffect(() => {
    const timer = setTimeout(() => {
      resetProcessing();
      router.replace("/dashboard/upload");
    }, 2800);

    return () => clearTimeout(timer);
  }, [router, resetProcessing]);

  return (
    <div className="flex min-h-[calc(100vh-10rem)] items-center justify-center">
      <Card className="w-full max-w-xl">
        <CardHeader>
          <CardTitle className="text-2xl font-semibold">
            Task creation failed
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-3">
          <p className="text-sm text-text-secondary">{reason}</p>
          <p className="text-xs text-text-secondary">
            Redirecting you back to upload transcript...
          </p>
        </CardContent>
      </Card>
    </div>
  );
}

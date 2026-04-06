"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { useAppStore } from "@/store/useAppStore";

export default function CancelledPage() {
  const router = useRouter();
  const resetProcessing = useAppStore((state) => state.resetProcessing);

  useEffect(() => {
    const timer = setTimeout(() => {
      resetProcessing();
      router.replace("/dashboard/upload");
    }, 1800);

    return () => clearTimeout(timer);
  }, [router, resetProcessing]);

  return (
    <div className="flex min-h-[calc(100vh-10rem)] items-center justify-center">
      <Card className="w-full max-w-lg">
        <CardHeader>
          <CardTitle className="text-2xl font-semibold">Task creation cancelled</CardTitle>
        </CardHeader>
        <CardContent>
          <p className="text-sm text-text-secondary">
            Redirecting you back to upload transcript...
          </p>
        </CardContent>
      </Card>
    </div>
  );
}

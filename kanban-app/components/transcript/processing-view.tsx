import { LoaderCircle } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { PROCESSING_STEPS } from "@/types";

interface ProcessingViewProps {
  currentStep: number;
}

export function ProcessingView({ currentStep }: ProcessingViewProps) {
  return (
    <Card className="w-full max-w-2xl">
      <CardHeader>
        <CardTitle className="text-2xl font-semibold">Processing transcript</CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="flex items-center gap-3 rounded-xl bg-muted/70 p-4">
          <LoaderCircle className="h-5 w-5 animate-spin text-primary" />
          <p className="text-sm text-text-primary">
            {PROCESSING_STEPS[currentStep] ?? PROCESSING_STEPS[0]}
          </p>
        </div>

        <div className="grid gap-2">
          {PROCESSING_STEPS.map((step, index) => {
            const completed = index < currentStep;
            const active = index === currentStep;

            return (
              <div
                key={step}
                className={`flex items-center justify-between rounded-xl border p-3 ${
                  completed
                    ? "border-primary/40 bg-primary/15"
                    : active
                      ? "border-accent-yellow bg-accent-yellow/20"
                      : "border-border bg-card"
                }`}
              >
                <span className="text-sm text-text-primary">{step}</span>
                <Badge
                  variant={completed ? "primary" : active ? "warning" : "default"}
                >
                  {completed ? "Done" : active ? "Running" : "Pending"}
                </Badge>
              </div>
            );
          })}
        </div>
      </CardContent>
    </Card>
  );
}

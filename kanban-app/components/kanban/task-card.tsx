import { CalendarDays, Link as LinkIcon } from "lucide-react";

import { AvatarGroup } from "@/components/shared/avatar-group";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent } from "@/components/ui/card";
import { getTaskUrgency } from "@/lib/tasks";
import type { Task, User } from "@/types";

interface TaskCardProps {
  task: Task;
  cardIndex?: number;
  usersMap: Map<string, User>;
}

export function TaskCard({ task, cardIndex = 0, usersMap }: TaskCardProps) {
  const urgency = getTaskUrgency(task.deadline);
  const assignees = task.assigneeIds
    .map((id) => usersMap.get(id))
    .filter((entry): entry is User => Boolean(entry));

  const urgencyClass =
    urgency === "overdue"
      ? "bg-danger/30"
      : urgency === "near"
        ? "bg-accent-yellow/35"
        : "bg-card";

  return (
    <Card
      className={`${urgencyClass} kbn-pop-in kbn-card-lift`}
      style={{ animationDelay: `${Math.min(cardIndex, 8) * 35}ms` }}
    >
      <CardContent className="space-y-3 p-4">
        <div className="space-y-1">
          <h4 className="text-sm font-medium text-text-primary">{task.title}</h4>
          <p className="line-clamp-2 text-sm text-text-secondary">{task.description}</p>
        </div>

        <div className="flex items-center justify-between">
          <div className="inline-flex items-center gap-1 text-xs text-text-secondary">
            <CalendarDays className="h-3.5 w-3.5" />
            <span>{new Date(task.deadline).toLocaleDateString()}</span>
          </div>
          {urgency === "overdue" ? (
            <Badge variant="danger">Overdue</Badge>
          ) : urgency === "near" ? (
            <Badge variant="warning">Near deadline</Badge>
          ) : (
            <Badge>On track</Badge>
          )}
        </div>

        <div className="flex items-center justify-between">
          <AvatarGroup users={assignees} />
          <div className="inline-flex items-center gap-1 text-xs text-text-secondary">
            <LinkIcon className="h-3.5 w-3.5" />
            {task.transcriptReference}
          </div>
        </div>
      </CardContent>
    </Card>
  );
}

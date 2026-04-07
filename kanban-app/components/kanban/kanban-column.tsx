import { AddTaskModal } from "@/components/tasks/add-task-modal";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import type { Task, TaskStatus, User } from "@/types";

import { TaskCard } from "./task-card";

interface KanbanColumnProps {
  title: string;
  status: TaskStatus;
  tasks: Task[];
  projectId: string;
  usersMap: Map<string, User>;
  loading?: boolean;
}

export function KanbanColumn({
  title,
  status,
  tasks,
  projectId,
  usersMap,
  loading,
}: KanbanColumnProps) {
  const columnDelayClass =
    status === "todo"
      ? "kbn-delay-1"
      : status === "in-progress"
        ? "kbn-delay-2"
        : "kbn-delay-3";

  return (
    <div className={`kbn-fade-up ${columnDelayClass} flex min-h-[26rem] flex-col rounded-xl border border-border bg-card shadow-sm`}>
      <div className="flex items-center justify-between gap-2 border-b border-border p-4">
        <div className="flex items-center gap-2">
          <h3 className="text-xl font-medium text-text-primary">{title}</h3>
          <Badge variant="primary">{tasks.length}</Badge>
        </div>
        <AddTaskModal projectId={projectId} status={status} />
      </div>

      <div className="space-y-3 p-4">
        {loading
          ? Array.from({ length: 3 }).map((_, index) => (
              <Skeleton key={`skeleton-${index}`} className="h-28 w-full" />
            ))
          : tasks.map((task, index) => (
              <TaskCard key={task.id} task={task} cardIndex={index} usersMap={usersMap} />
            ))}

        {!loading && tasks.length === 0 ? (
          <div className="rounded-xl border border-dashed border-border bg-muted/40 p-4 text-center text-sm text-text-secondary">
            No tasks in this column.
          </div>
        ) : null}
      </div>
    </div>
  );
}

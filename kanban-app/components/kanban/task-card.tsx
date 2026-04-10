"use client";

import {
  CalendarDays,
  Link as LinkIcon,
  Loader2,
  MoreVertical,
} from "lucide-react";
import { useRouter } from "next/navigation";
import { useState } from "react";

import { Badge } from "@/components/ui/badge";
import { Avatar, AvatarFallback } from "@/components/ui/avatar";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { getTaskUrgency, updateTaskApi } from "@/lib/tasks";
import { useAppStore } from "@/store/useAppStore";
import type { Task, TaskStatus } from "@/types";

const getAssigneeInitials = (name?: string) => {
  if (!name) return "-";

  const initials = name
    .split(/\s+/)
    .filter(Boolean)
    .map((part) => part[0])
    .join("")
    .slice(0, 2)
    .toUpperCase();

  return initials || name.slice(0, 2).toUpperCase();
};

const formatDeadline = (deadline?: string) => {
  if (!deadline) {
    return "No deadline";
  }

  const dateOnly = /^(\d{4})-(\d{2})-(\d{2})$/.exec(deadline);
  if (dateOnly) {
    const [, y, m, d] = dateOnly;
    return new Date(Number(y), Number(m) - 1, Number(d)).toLocaleDateString();
  }

  const parsed = new Date(deadline);
  if (Number.isNaN(parsed.getTime())) {
    return "No deadline";
  }
  return parsed.toLocaleDateString();
};

interface TaskCardProps {
  task: Task;
  cardIndex?: number;
  assigneeName?: string;
  onEdit?: (task: Task) => void;
  onStatusChange?: (task: Task) => void;
}

export function TaskCard({
  task,
  cardIndex = 0,
  assigneeName,
  onEdit,
  onStatusChange,
}: TaskCardProps) {
  const router = useRouter();
  const urgency = getTaskUrgency(task.deadline);
  const [statusChanging, setStatusChanging] = useState(false);
  const updateTaskInStore = useAppStore((state) => state.updateTask);
  const setSelectedProject = useAppStore((state) => state.setSelectedProject);
  const setActiveTranscript = useAppStore((state) => state.setActiveTranscript);
  const currentUser = useAppStore((state) => state.user);
  const isManager = currentUser?.role === "manager";

  const urgencyClass =
    urgency === "overdue"
      ? "border-red-300 bg-red-100"
      : urgency === "near"
        ? "border-amber-300 bg-amber-100"
        : "bg-card";

  const handleStatusChange = async (newStatus: TaskStatus) => {
    if (newStatus === task.status || statusChanging) return;

    setStatusChanging(true);
    const previousStatus = task.status;

    // Move the task instantly for better UX, then persist to backend.
    updateTaskInStore(task.id, { status: newStatus });

    try {
      const updated = await updateTaskApi(task.id, { status: newStatus });
      updateTaskInStore(task.id, { status: updated.status });
      if (onStatusChange) {
        onStatusChange(updated);
      }
    } catch (error) {
      console.error("Failed to update status:", error);
      updateTaskInStore(task.id, { status: previousStatus });
    } finally {
      setStatusChanging(false);
    }
  };

  const handleOpenTranscript = () => {
    if (!task.transcriptReference) return;
    setSelectedProject(task.projectId);
    setActiveTranscript(task.transcriptReference);
    router.push(`/dashboard/publish?transcriptId=${task.transcriptReference}`);
  };

  return (
    <Card
      className={`${urgencyClass} kbn-pop-in kbn-card-lift`}
      style={{ animationDelay: `${Math.min(cardIndex, 8) * 35}ms` }}
    >
      <CardContent className="space-y-3 p-4">
        <div className="flex items-start justify-between gap-2">
          <div className="flex-1 space-y-1">
            <h4 className="text-sm font-medium text-text-primary">
              {task.title}
            </h4>
            <p className="line-clamp-2 text-sm text-text-secondary">
              {task.description}
            </p>
          </div>
          {onEdit && (
            <DropdownMenu>
              <DropdownMenuTrigger asChild>
                <Button variant="ghost" size="sm" className="h-6 w-6 p-0">
                  <MoreVertical className="h-4 w-4" />
                </Button>
              </DropdownMenuTrigger>
              <DropdownMenuContent align="end">
                <DropdownMenuItem onClick={() => onEdit(task)}>
                  Edit Details
                </DropdownMenuItem>
              </DropdownMenuContent>
            </DropdownMenu>
          )}
        </div>

        <div className="flex items-center justify-between gap-2">
          <div className="inline-flex items-center gap-1 text-xs text-text-secondary">
            <CalendarDays className="h-3.5 w-3.5" />
            <span>{formatDeadline(task.deadline)}</span>
          </div>
          {!task.deadline ? (
            <Badge>Unset</Badge>
          ) : urgency === "overdue" ? (
            <Badge variant="danger">Overdue</Badge>
          ) : urgency === "near" ? (
            <Badge variant="warning">Near deadline</Badge>
          ) : (
            <Badge>On track</Badge>
          )}
        </div>

        <div className="flex items-center justify-between gap-2">
          <Select
            value={task.status}
            onValueChange={(val) => handleStatusChange(val as TaskStatus)}
            disabled={statusChanging || !isManager}
          >
            <SelectTrigger className="h-7 w-32 text-xs">
              {statusChanging ? (
                <Loader2 className="h-3 w-3 animate-spin" />
              ) : (
                <SelectValue />
              )}
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="todo">To Do</SelectItem>
              <SelectItem value="in-progress">In Progress</SelectItem>
              <SelectItem value="completed">Completed</SelectItem>
            </SelectContent>
          </Select>

          <div
            className="inline-flex items-center gap-2"
            title={assigneeName || "Unassigned"}
          >
            <Avatar className="h-8 w-8 border border-border">
              <AvatarFallback className="bg-primary/20 text-[10px] font-semibold uppercase tracking-wide">
                {getAssigneeInitials(assigneeName)}
              </AvatarFallback>
            </Avatar>
          </div>

          <div className="inline-flex items-center gap-1 text-xs text-text-secondary">
            <LinkIcon className="h-3.5 w-3.5" />
            {task.transcriptReference ? (
              <button
                type="button"
                onClick={handleOpenTranscript}
                className="max-w-40 truncate text-left underline-offset-2 hover:underline"
                title="Open meeting summary"
              >
                {task.transcriptReference}
              </button>
            ) : (
              <span>-</span>
            )}
          </div>
        </div>
      </CardContent>
    </Card>
  );
}

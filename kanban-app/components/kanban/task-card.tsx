"use client";

import { Loader2, MoreVertical } from "lucide-react";
import { useState } from "react";
import { CalendarDays, Link as LinkIcon } from "lucide-react";

import { Avatar, AvatarFallback } from "@/components/ui/avatar";
import { Badge } from "@/components/ui/badge";
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
import type { Task, TaskStatus } from "@/types";

interface TaskCardProps {
  task: Task;
  cardIndex?: number;
  onEdit?: (task: Task) => void;
  onStatusChange?: (task: Task) => void;
}

export function TaskCard({
  task,
  cardIndex = 0,
  onEdit,
  onStatusChange,
}: TaskCardProps) {
  const urgency = getTaskUrgency(task.deadline);
  const [statusChanging, setStatusChanging] = useState(false);

  const urgencyClass =
    urgency === "overdue"
      ? "bg-danger/30"
      : urgency === "near"
        ? "bg-accent-yellow/35"
        : "bg-card";

  const handleStatusChange = async (newStatus: TaskStatus) => {
    setStatusChanging(true);
    try {
      const updated = await updateTaskApi(task.id, { status: newStatus });
      if (onStatusChange) {
        onStatusChange(updated);
      }
    } catch (error) {
      console.error("Failed to update status:", error);
    } finally {
      setStatusChanging(false);
    }
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

        <div className="flex items-center justify-between gap-2">
          <Select
            value={task.status}
            onValueChange={(val) => handleStatusChange(val as TaskStatus)}
            disabled={statusChanging}
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

          <div className="inline-flex items-center gap-1 text-xs text-text-secondary">
            <LinkIcon className="h-3.5 w-3.5" />
            <span>{task.transcriptReference || "—"}</span>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}

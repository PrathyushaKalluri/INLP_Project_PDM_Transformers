"use client";

import { useState } from "react";
import { Calendar, Loader2 } from "lucide-react";

import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { useAppStore } from "@/store/useAppStore";
import { createTaskApi } from "@/lib/tasks";
import type { TaskStatus } from "@/types";

interface CreateTaskModalProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  projectId: string;
  status: TaskStatus;
  onTaskCreated?: () => void;
}

export function CreateTaskModal({
  open,
  onOpenChange,
  projectId,
  status,
  onTaskCreated,
}: CreateTaskModalProps) {
  const user = useAppStore((state) => state.user);
  const addTask = useAppStore((state) => state.addTask);
  const addNotification = useAppStore((state) => state.addNotification);

  const [title, setTitle] = useState("");
  const [description, setDescription] = useState("");
  const [dueDate, setDueDate] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const canSave = title.trim().length > 2;

  const reset = () => {
    setTitle("");
    setDescription("");
    setDueDate("");
    setError(null);
  };

  const save = async () => {
    if (!canSave || !user) {
      return;
    }

    setLoading(true);
    setError(null);

    try {
      const created = await createTaskApi({
        project_id: projectId,
        title: title.trim(),
        description: description.trim() || undefined,
        due_date: dueDate || undefined,
        status,
        assignee_id: user.id,
      });

      // Add to store
      addTask(created);

      addNotification({
        message: "Task created successfully",
        type: "success",
      });

      onOpenChange(false);
      reset();
      onTaskCreated?.();
    } catch (err) {
      const errorMsg =
        err instanceof Error ? err.message : "Failed to create task";
      setError(errorMsg);
      addNotification({
        message: `Error: ${errorMsg}`,
        type: "warning",
      });
    } finally {
      setLoading(false);
    }
  };

  return (
    <Dialog
      open={open}
      onOpenChange={(next) => {
        onOpenChange(next);
        if (!next) {
          reset();
        }
      }}
    >
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Create new task</DialogTitle>
          <DialogDescription>
            Add a task to{" "}
            {status === "todo"
              ? "To-Do"
              : status === "in-progress"
                ? "In Progress"
                : "Completed"}
            .
          </DialogDescription>
        </DialogHeader>

        <div className="grid gap-4">
          <div className="grid gap-2">
            <Label htmlFor="task-title">Title *</Label>
            <Input
              id="task-title"
              placeholder="Task title..."
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              disabled={loading}
              maxLength={500}
            />
            <p className="text-xs text-text-secondary">{title.length}/500</p>
          </div>

          <div className="grid gap-2">
            <Label htmlFor="task-description">Description</Label>
            <Textarea
              id="task-description"
              placeholder="Add details about this task..."
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              disabled={loading}
              rows={3}
              className="resize-none"
            />
          </div>

          <div className="grid gap-2">
            <Label htmlFor="task-deadline" className="flex items-center gap-2">
              <Calendar className="h-4 w-4" />
              Due date
            </Label>
            <Input
              id="task-deadline"
              type="date"
              value={dueDate}
              onChange={(e) => setDueDate(e.target.value)}
              disabled={loading}
            />
          </div>

          {error && (
            <div className="rounded-lg border border-orange-500 bg-orange-50 p-2 text-sm text-orange-700">
              {error}
            </div>
          )}
        </div>

        <DialogFooter>
          <Button
            variant="ghost"
            onClick={() => onOpenChange(false)}
            disabled={loading}
          >
            Cancel
          </Button>
          <Button disabled={!canSave || loading} onClick={save}>
            {loading && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
            {loading ? "Creating..." : "Create"}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

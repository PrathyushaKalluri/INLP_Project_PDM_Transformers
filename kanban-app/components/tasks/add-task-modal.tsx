"use client";

import { useState } from "react";
import { Calendar, Loader2, Plus } from "lucide-react";

import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { useAppStore } from "@/store/useAppStore";
import { createTaskApi } from "@/lib/tasks";
import type { TaskStatus } from "@/types";

interface AddTaskModalProps {
  projectId: string;
  status: TaskStatus;
  triggerLabel?: string;
}

export function AddTaskModal({
  projectId,
  status,
  triggerLabel = "Add Task",
}: AddTaskModalProps) {
  const user = useAppStore((state) => state.user);
  const addTask = useAppStore((state) => state.addTask);
  const addNotification = useAppStore((state) => state.addNotification);

  const [open, setOpen] = useState(false);
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

  const handleOpenChange = (newOpen: boolean) => {
    setOpen(newOpen);
    if (!newOpen) {
      reset();
    }
  };

  const onSubmit = async () => {
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

      handleOpenChange(false);
      reset();
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
    <Dialog open={open} onOpenChange={handleOpenChange}>
      <DialogTrigger asChild>
        <Button variant="secondary" size="sm" className="gap-1">
          <Plus className="h-4 w-4" />
          {triggerLabel}
        </Button>
      </DialogTrigger>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Add task</DialogTitle>
          <DialogDescription>
            Create a new task in{" "}
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
              placeholder="Define the task"
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
              placeholder="Describe expected outcome"
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
            onClick={() => handleOpenChange(false)}
            disabled={loading}
          >
            Cancel
          </Button>
          <Button onClick={onSubmit} disabled={!canSave || loading}>
            {loading && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
            {loading ? "Creating..." : "Save task"}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

"use client";

import { useMemo, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

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
import { getProjects } from "@/lib/api/projects.api";
import { buildUserDirectory } from "@/lib/api/user-directory";
import { createTask } from "@/lib/api/tasks.api";
import { queryKeys } from "@/lib/api/query-keys";
import { getErrorMessage } from "@/lib/utils";
import { useToast } from "@/components/ui/use-toast";
import { useAppStore } from "@/store/useAppStore";
import type { User } from "@/types";

interface AddTaskModalProps {
  projectId: string;
  status: "todo" | "in-progress" | "completed";
  triggerLabel?: string;
}

export function AddTaskModal({
  projectId,
  status,
  triggerLabel = "+ Add Task",
}: AddTaskModalProps) {
  const { toast } = useToast();
  const queryClient = useQueryClient();
  const user = useAppStore((state) => state.user);
  const [open, setOpen] = useState(false);
  const [title, setTitle] = useState("");
  const [description, setDescription] = useState("");
  const [deadline, setDeadline] = useState("");
  const [assignees, setAssignees] = useState<string[]>([]);

  const projectsQuery = useQuery({
    queryKey: queryKeys.projects,
    queryFn: getProjects,
  });

  const users: User[] = useMemo(() => {
    const project = (projectsQuery.data ?? []).find((entry) => entry.id === projectId);
    const directory = buildUserDirectory(user, project?.participants ?? []);
    return Array.from(directory.values());
  }, [projectsQuery.data, projectId, user]);

  const createTaskMutation = useMutation({
    mutationFn: createTask,
    onSuccess: () => {
      queryClient.invalidateQueries({
        queryKey: queryKeys.tasks(projectId),
      });
      reset();
      setOpen(false);
    },
    onError: (error) => {
      toast({
        title: "Failed to save task",
        description: getErrorMessage(error),
      });
    },
  });

  const canSubmit = useMemo(
    () => title.trim().length > 2 && description.trim().length > 4 && deadline,
    [title, description, deadline]
  );

  const toggleAssignee = (id: string) => {
    setAssignees((prev) =>
      prev.includes(id) ? prev.filter((entry) => entry !== id) : [...prev, id]
    );
  };

  const reset = () => {
    setTitle("");
    setDescription("");
    setDeadline("");
    setAssignees([]);
  };

  const onSubmit = async () => {
    if (!canSubmit) {
      return;
    }

    await createTaskMutation.mutateAsync({
      projectId,
      title: title.trim(),
      description: description.trim(),
      deadline,
      assigneeIds: assignees,
      transcriptReference: "Manual Task",
      status,
    });
  };

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger asChild>
        <Button variant="secondary" size="sm">
          {triggerLabel}
        </Button>
      </DialogTrigger>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Add task</DialogTitle>
          <DialogDescription>
            Create a new task and assign ownership.
          </DialogDescription>
        </DialogHeader>

        <div className="grid gap-4">
          <div className="grid gap-2">
            <Label htmlFor="task-title">Title</Label>
            <Input
              id="task-title"
              placeholder="Define the task"
              value={title}
              onChange={(event) => setTitle(event.target.value)}
            />
          </div>

          <div className="grid gap-2">
            <Label htmlFor="task-description">Description</Label>
            <Textarea
              id="task-description"
              placeholder="Describe expected outcome"
              value={description}
              onChange={(event) => setDescription(event.target.value)}
            />
          </div>

          <div className="grid gap-2">
            <Label htmlFor="task-deadline">Deadline</Label>
            <Input
              id="task-deadline"
              type="date"
              value={deadline}
              onChange={(event) => setDeadline(event.target.value)}
            />
          </div>

          <div className="grid gap-2">
            <Label>Assignees</Label>
            <div className="grid grid-cols-1 gap-2 sm:grid-cols-2">
              {users.map((user) => {
                const active = assignees.includes(user.id);
                return (
                  <button
                    key={user.id}
                    type="button"
                    onClick={() => toggleAssignee(user.id)}
                    className={`rounded-xl border px-3 py-2 text-left text-sm transition-colors ${
                      active
                        ? "border-primary bg-primary/20 text-text-primary"
                        : "border-border bg-card text-text-secondary hover:bg-muted"
                    }`}
                  >
                    {user.name}
                  </button>
                );
              })}
            </div>
          </div>
        </div>

        <DialogFooter>
          <Button variant="ghost" onClick={() => setOpen(false)}>
            Cancel
          </Button>
          <Button onClick={onSubmit} disabled={!canSubmit || createTaskMutation.isPending}>
            Save task
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

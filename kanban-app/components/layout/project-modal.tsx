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
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { createProject, getProjects, setProjectParticipants, updateProject } from "@/lib/api/projects.api";
import { queryKeys } from "@/lib/api/query-keys";
import { buildUserDirectory } from "@/lib/api/user-directory";
import { getErrorMessage } from "@/lib/utils";
import { useToast } from "@/components/ui/use-toast";
import { useAppStore } from "@/store/useAppStore";

interface ProjectModalProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  projectId?: string | null;
}

export function ProjectModal({
  open,
  onOpenChange,
  projectId,
}: ProjectModalProps) {
  const { toast } = useToast();
  const queryClient = useQueryClient();
  const user = useAppStore((state) => state.user);

  const projectsQuery = useQuery({
    queryKey: queryKeys.projects,
    queryFn: getProjects,
  });

  const projects = useMemo(() => projectsQuery.data ?? [], [projectsQuery.data]);
  const editing = useMemo(
    () => projects.find((project) => project.id === projectId),
    [projects, projectId]
  );

  const directory = useMemo(() => {
    const ids: string[] = [];
    projects.forEach((project) => {
      ids.push(...project.participants);
    });
    return buildUserDirectory(user, ids);
  }, [projects, user]);

  const users = useMemo(() => Array.from(directory.values()), [directory]);

  const createProjectMutation = useMutation({
    mutationFn: async (payload: { name: string; description: string; participantIds: string[] }) => {
      const project = await createProject({
        name: payload.name,
        description: payload.description,
      });
      if (payload.participantIds.length > 0) {
        await setProjectParticipants(project.id, payload.participantIds);
      }
      return project;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.projects });
      onOpenChange(false);
      reset();
    },
    onError: (error) => {
      toast({
        title: "Failed to create project",
        description: getErrorMessage(error),
      });
    },
  });

  const updateProjectMutation = useMutation({
    mutationFn: async () => {
      if (!editing) {
        return;
      }
      await updateProject(editing.id, {
        name: name.trim(),
        description: description.trim(),
      });
      await setProjectParticipants(editing.id, participants);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.projects });
      onOpenChange(false);
      reset();
    },
    onError: (error) => {
      toast({
        title: "Failed to update project",
        description: getErrorMessage(error),
      });
    },
  });

  const [draftsByProject, setDraftsByProject] = useState<
    Record<string, { name: string; description: string; participants: string[] }>
  >({});

  const draftKey = projectId ?? "new";

  const activeDraft = draftsByProject[draftKey] ?? {
    name: editing?.name ?? "",
    description: editing?.description ?? "",
    participants: editing?.participants ?? [],
  };

  const name = activeDraft.name;
  const description = activeDraft.description;
  const participants = activeDraft.participants;

  const canSave = name.trim().length > 2 && description.trim().length > 4;

  const reset = () => {
    setDraftsByProject((prev) => {
      const next = { ...prev };
      delete next[draftKey];
      return next;
    });
  };

  const toggleParticipant = (userId: string) => {
    setDraftsByProject((prev) => {
      const current = prev[draftKey] ?? activeDraft;
      const nextParticipants = current.participants.includes(userId)
        ? current.participants.filter((entry) => entry !== userId)
        : [...current.participants, userId];

      return {
        ...prev,
        [draftKey]: {
          ...current,
          participants: nextParticipants,
        },
      };
    });
  };

  const save = async () => {
    if (!canSave) {
      return;
    }

    if (editing) {
      await updateProjectMutation.mutateAsync();
    } else {
      await createProjectMutation.mutateAsync({
        name: name.trim(),
        description: description.trim(),
        participantIds: participants,
      });
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
          <DialogTitle>{editing ? "Edit project" : "Add project"}</DialogTitle>
          <DialogDescription>
            Managers can add and update project details.
          </DialogDescription>
        </DialogHeader>

        <div className="grid gap-4">
          <div className="grid gap-2">
            <Label htmlFor="project-name">Project name</Label>
              <Input
                id="project-name"
                value={name}
                onChange={(event) => {
                  const nextName = event.target.value;
                  setDraftsByProject((prev) => ({
                    ...prev,
                    [draftKey]: {
                      ...activeDraft,
                      name: nextName,
                    },
                  }));
                }}
              />
            </div>
            <div className="grid gap-2">
              <Label htmlFor="project-description">Description</Label>
              <Textarea
                id="project-description"
                value={description}
                onChange={(event) => {
                  const nextDescription = event.target.value;
                  setDraftsByProject((prev) => ({
                    ...prev,
                    [draftKey]: {
                      ...activeDraft,
                      description: nextDescription,
                    },
                  }));
                }}
              />
            </div>
          <div className="grid gap-2">
            <Label>Add participants</Label>
            <div className="grid grid-cols-1 gap-2 sm:grid-cols-2">
              {users.map((user) => {
                const selected = participants.includes(user.id);
                return (
                  <button
                    key={user.id}
                    type="button"
                    onClick={() => toggleParticipant(user.id)}
                    className={`rounded-xl border px-3 py-2 text-left text-sm transition-colors ${
                      selected
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
          <Button variant="ghost" onClick={() => onOpenChange(false)}>
            Cancel
          </Button>
          <Button
            disabled={
              !canSave || createProjectMutation.isPending || updateProjectMutation.isPending
            }
            onClick={save}
          >
            Save
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

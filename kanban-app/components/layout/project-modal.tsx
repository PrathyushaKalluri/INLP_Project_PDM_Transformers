"use client";

import { useMemo, useState } from "react";

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
import { mockUsers, useAppStore } from "@/store/useAppStore";

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
  const addProject = useAppStore((state) => state.addProject);
  const updateProject = useAppStore((state) => state.updateProject);
  const projects = useAppStore((state) => state.projects);
  const editing = useMemo(
    () => projects.find((project) => project.id === projectId),
    [projects, projectId]
  );

  const [name, setName] = useState(editing?.name ?? "");
  const [description, setDescription] = useState(editing?.description ?? "");
  const [participants, setParticipants] = useState<string[]>(
    editing?.participants ?? []
  );

  const canSave = name.trim().length > 2 && description.trim().length > 4;

  const reset = () => {
    setName(editing?.name ?? "");
    setDescription(editing?.description ?? "");
    setParticipants(editing?.participants ?? []);
  };

  const toggleParticipant = (userId: string) => {
    setParticipants((prev) =>
      prev.includes(userId)
        ? prev.filter((entry) => entry !== userId)
        : [...prev, userId]
    );
  };

  const save = () => {
    if (!canSave) {
      return;
    }

    if (editing) {
      updateProject(editing.id, {
        name: name.trim(),
        description: description.trim(),
        participants,
      });
    } else {
      addProject({
        name: name.trim(),
        description: description.trim(),
        participants,
      });
    }

    onOpenChange(false);
    reset();
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
              onChange={(event) => setName(event.target.value)}
            />
          </div>
          <div className="grid gap-2">
            <Label htmlFor="project-description">Description</Label>
            <Textarea
              id="project-description"
              value={description}
              onChange={(event) => setDescription(event.target.value)}
            />
          </div>
          <div className="grid gap-2">
            <Label>Add participants</Label>
            <div className="grid grid-cols-1 gap-2 sm:grid-cols-2">
              {mockUsers.map((user) => {
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
          <Button disabled={!canSave} onClick={save}>
            Save
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

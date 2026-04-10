"use client";

import { useEffect, useMemo, useState } from "react";
import { Loader2 } from "lucide-react";

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
import { createProject, updateProject } from "@/lib/projects";
import { listAllUsers } from "@/lib/users";
import { listTeamsApi, type Team } from "@/lib/teams";
import type { User } from "@/types";

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
  const user = useAppStore((state) => state.user);
  const addProject = useAppStore((state) => state.addProject);
  const updateProjectStore = useAppStore((state) => state.updateProject);
  const projects = useAppStore((state) => state.projects);
  const addNotification = useAppStore((state) => state.addNotification);

  const editing = useMemo(
    () => projects.find((project) => project.id === projectId),
    [projects, projectId],
  );

  const [name, setName] = useState(editing?.name ?? "");
  const [description, setDescription] = useState(editing?.description ?? "");
  const [participants, setParticipants] = useState<string[]>(
    editing?.participants ?? [],
  );
  const [users, setUsers] = useState<User[]>([]);
  const [teams, setTeams] = useState<Team[]>([]);
  const [selectedTeam, setSelectedTeam] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [teamsLoading, setTeamsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Fetch users and teams on mount
  useEffect(() => {
    const fetchData = async () => {
      try {
        setTeamsLoading(true);

        // Fetch teams first
        const userTeams = await listTeamsApi();
        setTeams(userTeams);

        // Use first team by default
        if (userTeams.length > 0) {
          setSelectedTeam(userTeams[0].id);
        } else {
          setError("No teams found. Please contact your administrator.");
        }

        // Fetch users only if editing a project
        if (editing) {
          try {
            const allUsers = await listAllUsers();
            setUsers(allUsers);
          } catch (err) {
            console.error("Failed to fetch users:", err);
            // Non-critical error, don't show to user
          }
        }
      } catch (err) {
        const msg = err instanceof Error ? err.message : "Failed to load teams";
        console.error("Failed to fetch data:", err);
        setError(msg);
      } finally {
        setTeamsLoading(false);
      }
    };

    fetchData();
  }, [editing]);

  const canSave =
    name.trim().length >= 3 &&
    description.trim().length >= 5 &&
    !!selectedTeam &&
    !!user;

  const reset = () => {
    setName(editing?.name ?? "");
    setDescription(editing?.description ?? "");
    setParticipants(editing?.participants ?? []);
    setError(null);
  };

  const toggleParticipant = (userId: string) => {
    setParticipants((prev) =>
      prev.includes(userId)
        ? prev.filter((entry) => entry !== userId)
        : [...prev, userId],
    );
  };

  const save = async () => {
    console.log("[ProjectModal] Save clicked:", {
      canSave,
      name: name.trim(),
      description: description.trim(),
      selectedTeam,
      isLoading: loading,
    });

    if (!canSave || !user || !selectedTeam) {
      console.log("[ProjectModal] ✗ Cannot save - validation failed:", {
        valid: canSave,
        hasUser: !!user,
        hasTeam: !!selectedTeam,
      });
      return;
    }

    console.log("[ProjectModal] ✓ Validation passed, proceeding with save");

    setLoading(true);
    setError(null);

    try {
      if (editing) {
        // Update existing project via API
        console.log("[ProjectModal] Updating project:", editing.id);
        const updated = await updateProject(editing.id, {
          name: name.trim(),
          description: description.trim(),
        });
        console.log("[ProjectModal] ✓ Project updated:", updated);
        updateProjectStore(editing.id, updated);
        addNotification({
          message: "Project updated successfully",
          type: "success",
        });
      } else {
        // Create new project via API using selected team
        console.log("[ProjectModal] Creating new project:", {
          team_id: selectedTeam,
          name: name.trim(),
          description: description.trim(),
        });
        const created = await createProject({
          team_id: selectedTeam,
          name: name.trim(),
          description: description.trim(),
        });
        console.log("[ProjectModal] ✓ Project created:", created);
        addProject(created);
        addNotification({
          message: "Project created successfully",
          type: "success",
        });
      }

      onOpenChange(false);
      reset();
    } catch (err) {
      const errorMsg =
        err instanceof Error ? err.message : "Failed to save project";
      console.error("[ProjectModal] ✗ Save failed:", { error: err, errorMsg });
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
              disabled={loading}
            />
          </div>
          <div className="grid gap-2">
            <Label htmlFor="project-description">Description</Label>
            <Textarea
              id="project-description"
              value={description}
              onChange={(event) => setDescription(event.target.value)}
              disabled={loading}
            />
          </div>

          {!editing && (
            <div className="grid gap-2">
              <Label htmlFor="team-select">
                Select Team {teamsLoading && "*"}
              </Label>
              <select
                id="team-select"
                value={selectedTeam || ""}
                onChange={(e) => setSelectedTeam(e.target.value)}
                disabled={loading || teamsLoading || teams.length === 0}
                className="rounded-md border border-border bg-card px-3 py-2 text-sm text-text-primary disabled:opacity-50"
              >
                {teamsLoading && <option value="">Loading teams...</option>}
                {!teamsLoading && teams.length === 0 && (
                  <option value="">No teams available</option>
                )}
                {!teamsLoading && teams.length > 0 && (
                  <>
                    <option value="">Choose a team...</option>
                    {teams.map((team) => (
                      <option key={team.id} value={team.id}>
                        {team.name}
                      </option>
                    ))}
                  </>
                )}
              </select>
            </div>
          )}

          {error && (
            <div className="rounded-lg border border-danger bg-danger/10 p-2 text-sm text-danger">
              {error}
            </div>
          )}

          {editing && users.length > 0 && (
            <div className="grid gap-2">
              <Label>Team members</Label>
              <div className="grid grid-cols-1 gap-2 sm:grid-cols-2">
                {users.map((u) => {
                  const selected = participants.includes(u.id);
                  return (
                    <button
                      key={u.id}
                      type="button"
                      onClick={() => toggleParticipant(u.id)}
                      disabled={loading}
                      className={`rounded-xl border px-3 py-2 text-left text-sm transition-colors ${
                        selected
                          ? "border-primary bg-primary/20 text-text-primary"
                          : "border-border bg-card text-text-secondary hover:bg-muted"
                      }`}
                    >
                      {u.name}
                    </button>
                  );
                })}
              </div>
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
            {loading ? "Saving..." : "Save"}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

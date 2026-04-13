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
import { listTeamsApi, type Team } from "@/lib/teams";

const TEAM_PAGE_SIZE = 25;

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
  const [teams, setTeams] = useState<Team[]>([]);
  const [selectedTeam, setSelectedTeam] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [teamsLoading, setTeamsLoading] = useState(true);
  const [teamsLoadingMore, setTeamsLoadingMore] = useState(false);
  const [teamSearch, setTeamSearch] = useState("");
  const [teamPage, setTeamPage] = useState(1);
  const [hasMoreTeams, setHasMoreTeams] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Keep form fields in sync with the currently selected project.
  useEffect(() => {
    if (!open) return;

    setName(editing?.name ?? "");
    setDescription(editing?.description ?? "");
    setSelectedTeam(editing?.teamId ?? null);
    setError(null);
  }, [open, editing?.id, editing?.name, editing?.description, editing?.teamId]);

  // Load teams for edit mode so we can display the assigned team name.
  useEffect(() => {
    if (!open || !editing?.teamId) return;

    let cancelled = false;

    const loadTeamsForEdit = async () => {
      try {
        const fetched = await listTeamsApi({ page: 1, limit: 100 });
        if (cancelled) return;
        setTeams(fetched);
      } catch {
        // Non-critical: fallback to raw team id when name is unavailable.
      }
    };

    void loadTeamsForEdit();
    return () => {
      cancelled = true;
    };
  }, [open, editing?.teamId]);

  // Reset search/pagination each time modal opens for create mode.
  useEffect(() => {
    if (!open || editing) return;
    setTeamSearch("");
    setTeamPage(1);
    setTeams([]);
    setSelectedTeam(null);
    setHasMoreTeams(false);
    setError(null);
  }, [open, editing]);

  // Load teams incrementally with search.
  useEffect(() => {
    if (!open || editing) return;

    let cancelled = false;
    const isFirstPage = teamPage === 1;

    const loadTeams = async () => {
      try {
        if (isFirstPage) {
          setTeamsLoading(true);
          setError(null);
        } else {
          setTeamsLoadingMore(true);
        }

        const fetched = await listTeamsApi({
          page: teamPage,
          limit: TEAM_PAGE_SIZE,
          search: teamSearch,
        });

        if (cancelled) return;

        setTeams((prev) => {
          if (isFirstPage) return fetched;
          const existing = new Set(prev.map((team) => team.id));
          const next = fetched.filter((team) => !existing.has(team.id));
          return [...prev, ...next];
        });

        setHasMoreTeams(fetched.length === TEAM_PAGE_SIZE);

        if (isFirstPage) {
          if (fetched.length > 0) {
            setSelectedTeam((prev) => prev ?? fetched[0].id);
          } else {
            setSelectedTeam(null);
            setError("No teams found. Try adjusting search.");
          }
        }
      } catch (err) {
        if (cancelled) return;
        const msg = err instanceof Error ? err.message : "Failed to load teams";
        console.error("Failed to fetch teams:", err);
        setError(msg);
      } finally {
        if (!cancelled) {
          setTeamsLoading(false);
          setTeamsLoadingMore(false);
        }
      }
    };

    const handle = setTimeout(loadTeams, 250);
    return () => {
      cancelled = true;
      clearTimeout(handle);
    };
  }, [open, editing, teamPage, teamSearch]);

  const trimmedName = name.trim();
  const trimmedDescription = description.trim();
  const hasValidContent =
    trimmedName.length >= 3 && trimmedDescription.length >= 5 && !!user;
  const detailsChanged =
    trimmedName !== (editing?.name ?? "").trim() ||
    trimmedDescription !== (editing?.description ?? "").trim();

  const canSave = editing
    ? hasValidContent && detailsChanged
    : hasValidContent && !!selectedTeam;

  const reset = () => {
    setName(editing?.name ?? "");
    setDescription(editing?.description ?? "");
    setSelectedTeam(editing?.teamId ?? null);
    setError(null);
  };

  const save = async () => {
    console.log("[ProjectModal] Save clicked:", {
      canSave,
      name: name.trim(),
      description: description.trim(),
      selectedTeam,
      isLoading: loading,
    });

    if (!canSave || !user || (!editing && !selectedTeam)) {
      console.log("[ProjectModal] ✗ Cannot save - validation failed:", {
        valid: canSave,
        hasUser: !!user,
        hasTeam: !!selectedTeam || !!editing,
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
        let updated = editing;
        if (detailsChanged) {
          updated = await updateProject(editing.id, {
            name: trimmedName,
            description: trimmedDescription,
          });
        }

        console.log("[ProjectModal] ✓ Project updated:", updated);
        updateProjectStore(editing.id, updated);
        addNotification({
          message: "Project updated successfully",
          type: "success",
        });
      } else {
        const teamId = selectedTeam;
        if (!teamId) {
          throw new Error("Team selection is required");
        }

        // Create new project via API using selected team
        console.log("[ProjectModal] Creating new project:", {
          team_id: teamId,
          name: name.trim(),
          description: description.trim(),
        });
        const created = await createProject({
          team_id: teamId,
          name: trimmedName,
          description: trimmedDescription,
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
              <Input
                id="team-search"
                value={teamSearch}
                onChange={(e) => {
                  setTeamSearch(e.target.value);
                  setTeamPage(1);
                }}
                placeholder="Search teams by name..."
                disabled={loading || teamsLoading}
              />
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
              {!teamsLoading && hasMoreTeams && (
                <Button
                  type="button"
                  variant="secondary"
                  onClick={() => setTeamPage((prev) => prev + 1)}
                  disabled={teamsLoadingMore || loading}
                >
                  {teamsLoadingMore ? "Loading more..." : "Load more teams"}
                </Button>
              )}
            </div>
          )}

          {editing && (
            <div className="grid gap-2">
              <Label htmlFor="assigned-team">Assigned team</Label>
              <Input
                id="assigned-team"
                value={
                  teams.find((team) => team.id === selectedTeam)?.name ||
                  selectedTeam ||
                  ""
                }
                readOnly
              />
              <p className="text-xs text-text-secondary">
                Manage team members from Team Management. Managers can add or
                remove team members there.
              </p>
            </div>
          )}

          {error && (
            <div className="rounded-lg border border-danger bg-danger/10 p-2 text-sm text-danger">
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
            {loading ? "Saving..." : "Save"}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

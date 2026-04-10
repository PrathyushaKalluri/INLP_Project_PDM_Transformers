"use client";

import { useEffect, useState } from "react";
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
import {
  createTeamApi,
  listWorkspacesApi,
  getOrCreateDefaultWorkspaceApi,
  addTeamMemberApi,
  type Workspace,
} from "@/lib/teams";
import { listAllUsers, toggleSeedDataMode, getSeedDataMode } from "@/lib/users";
import type { User } from "@/types";

// Local storage keys for workspace caching
const WORKSPACE_CACHE_KEY = "kanban_workspace_cache";

interface CachedWorkspace {
  id: string;
  name: string;
  slug: string;
  created_by: string;
  created_at: string;
}

// Helper to get cached workspace
function getCachedWorkspace(): CachedWorkspace | null {
  if (typeof window === "undefined") return null;
  const cached = window.localStorage.getItem(WORKSPACE_CACHE_KEY);
  return cached ? JSON.parse(cached) : null;
}

// Helper to cache workspace
function setCachedWorkspace(workspace: Workspace): void {
  if (typeof window === "undefined") return;
  window.localStorage.setItem(WORKSPACE_CACHE_KEY, JSON.stringify(workspace));
}

interface TeamModalProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onTeamCreated?: () => Promise<void>;
}

export function TeamModal({
  open,
  onOpenChange,
  onTeamCreated,
}: TeamModalProps) {
  const user = useAppStore((state) => state.user);
  const addNotification = useAppStore((state) => state.addNotification);

  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [selectedMembers, setSelectedMembers] = useState<string[]>([]);
  const [allUsers, setAllUsers] = useState<User[]>([]);
  const [workspace, setWorkspace] = useState<Workspace | null>(null);
  const [loading, setLoading] = useState(false);
  const [isInitializing, setIsInitializing] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [retryCount, setRetryCount] = useState(0);
  const [useSeedData, setUseSeedData] = useState(getSeedDataMode());

  const handleToggleSeedData = () => {
    const newValue = toggleSeedDataMode();
    setUseSeedData(newValue);
    addNotification({
      type: "info",
      message: newValue
        ? "Now using seed data for users"
        : "Now using backend API for users",
    });
  };

  useEffect(() => {
    if (!open) return;

    const fetchData = async () => {
      setIsInitializing(true);
      setError(null);
      setWorkspace(null);

      try {
        console.log("[TeamModal] Fetching workspaces...", { user });

        // Fetch workspaces from API
        const workspaces = await listWorkspacesApi();
        console.log("[TeamModal] Workspaces response:", workspaces);

        if (workspaces && workspaces.length > 0) {
          console.log("[TeamModal] Setting first workspace:", workspaces[0]);
          setWorkspace(workspaces[0]);
          // Cache it for future use
          setCachedWorkspace(workspaces[0]);
        } else {
          // No workspaces - try to get or create a default workspace
          console.log(
            "[TeamModal] No workspaces found, getting default workspace...",
          );
          try {
            const defaultWorkspace = await getOrCreateDefaultWorkspaceApi();
            console.log("[TeamModal] Got default workspace:", defaultWorkspace);
            setWorkspace(defaultWorkspace);
            setCachedWorkspace(defaultWorkspace);
          } catch (defaultErr) {
            // Fall back to cached workspace
            const cached = getCachedWorkspace();
            if (cached) {
              console.log("[TeamModal] Using cached workspace:", cached);
              setWorkspace(cached as Workspace);
            } else {
              const errorMsg =
                defaultErr instanceof Error
                  ? defaultErr.message
                  : "Failed to load workspaces. Please try again.";
              console.error(
                "[TeamModal] All workspace sources failed:",
                errorMsg,
              );
              setError(errorMsg);
            }
          }
        }

        // Fetch users for member selection
        const users = await listAllUsers();
        console.log("[TeamModal] Users response:", users);
        setAllUsers(users.filter((u) => u.id !== user?.id));
      } catch (err) {
        // Try to use cached workspace on error
        const cached = getCachedWorkspace();
        if (cached) {
          console.log(
            "[TeamModal] API failed, using cached workspace:",
            cached,
          );
          setWorkspace(cached as Workspace);
          // Don't set error since we have a workspace
        } else {
          const errorMsg =
            err instanceof Error
              ? err.message
              : "Failed to load workspaces. Ensure you are logged in.";
          console.error(
            "[TeamModal] Error and no cached workspace:",
            errorMsg,
            err,
          );
          setError(errorMsg);
        }
      } finally {
        setIsInitializing(false);
      }
    };

    fetchData();
  }, [open, user, retryCount]);

  const handleRetry = () => {
    setRetryCount((prev) => prev + 1);
  };

  const canSave = name.trim().length > 2 && workspace !== null && !error;

  const reset = () => {
    setName("");
    setDescription("");
    setSelectedMembers([]);
    setError(null);
  };

  const save = async () => {
    if (!canSave || !user || !workspace) {
      return;
    }

    setLoading(true);
    setError(null);

    try {
      // Create the team with the workspace ID
      const newTeam = await createTeamApi(workspace.id, {
        name: name.trim(),
        description: description.trim(),
      });

      // Add selected members to the team
      for (const memberId of selectedMembers) {
        try {
          await addTeamMemberApi(newTeam.id, memberId, "MEMBER");
        } catch (err) {
          console.error(`Failed to add member ${memberId}:`, err);
        }
      }

      addNotification({
        message: `Team "${name}" created successfully with ${selectedMembers.length} members`,
        type: "success",
      });

      // Notify parent to refresh teams
      if (onTeamCreated) {
        await onTeamCreated();
      }

      onOpenChange(false);
      reset();
    } catch (err) {
      const errorMsg =
        err instanceof Error ? err.message : "Failed to create team";
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
          <div className="flex items-center justify-between gap-4">
            <div className="flex-1">
              <DialogTitle>Create New Team</DialogTitle>
              <DialogDescription>
                Create a team and invite members to collaborate on projects.
              </DialogDescription>
            </div>
            <Button
              size="sm"
              variant={useSeedData ? "default" : "secondary"}
              onClick={handleToggleSeedData}
              title={useSeedData ? "Using seed data" : "Using backend API"}
              className="text-xs h-8 whitespace-nowrap"
            >
              {useSeedData ? "🌱 Seed" : "🔌 API"}
            </Button>
          </div>
        </DialogHeader>

        <div className="grid gap-4">
          {error && (
            <div className="rounded-lg border border-danger bg-danger/10 p-3 text-sm text-danger space-y-2">
              <div>{error}</div>
              <Button
                size="sm"
                variant="secondary"
                onClick={handleRetry}
                className="text-xs h-7"
              >
                🔄 Retry
              </Button>
            </div>
          )}

          {isInitializing && (
            <div className="flex items-center gap-2 py-4 justify-center">
              <Loader2 className="h-4 w-4 animate-spin" />
              <span className="text-sm text-text-secondary">
                Loading workspaces...
              </span>
            </div>
          )}

          <div className="grid gap-2">
            <Label htmlFor="team-name">Team name *</Label>
            <Input
              id="team-name"
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="e.g., Frontend Team, Backend Team"
              disabled={loading || isInitializing || !!error}
            />
          </div>

          <div className="grid gap-2">
            <Label htmlFor="team-description">Description</Label>
            <Textarea
              id="team-description"
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              placeholder="What is this team focused on?"
              disabled={loading || isInitializing || !!error}
            />
          </div>

          <div className="grid gap-2">
            <Label>Add Members</Label>
            {allUsers.length === 0 ? (
              <p className="text-sm text-text-secondary">
                No other users available to add
              </p>
            ) : (
              <div className="grid grid-cols-1 gap-2 sm:grid-cols-2 max-h-48 overflow-y-auto">
                {allUsers.map((u) => {
                  const selected = selectedMembers.includes(u.id);
                  return (
                    <button
                      key={u.id}
                      type="button"
                      onClick={() => {
                        setSelectedMembers((prev) =>
                          prev.includes(u.id)
                            ? prev.filter((id) => id !== u.id)
                            : [...prev, u.id],
                        );
                      }}
                      disabled={loading || isInitializing || !!error}
                      className={`rounded-lg border px-3 py-2 text-left text-sm transition-colors ${
                        selected
                          ? "border-primary bg-primary/20 text-text-primary"
                          : "border-border bg-card text-text-secondary hover:bg-muted"
                      }`}
                    >
                      <div className="font-medium">{u.name}</div>
                      <div className="text-xs opacity-70">{u.email}</div>
                    </button>
                  );
                })}
              </div>
            )}
            {selectedMembers.length > 0 && (
              <p className="text-xs text-text-secondary">
                {selectedMembers.length} member
                {selectedMembers.length !== 1 ? "s" : ""} selected
              </p>
            )}
          </div>
        </div>

        <DialogFooter>
          <Button
            variant="ghost"
            onClick={() => onOpenChange(false)}
            disabled={loading || isInitializing}
          >
            Cancel
          </Button>
          <Button disabled={!canSave || loading} onClick={save}>
            {loading && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
            Create Team
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

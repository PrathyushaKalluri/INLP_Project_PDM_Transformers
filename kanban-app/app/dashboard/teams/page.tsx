"use client";

import { useCallback, useEffect, useState } from "react";
import {
  Trash2,
  Plus,
  Edit2,
  ChevronRight,
  Users,
  Settings,
} from "lucide-react";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { useAppStore } from "@/store/useAppStore";
import {
  listTeamsApi,
  listTeamMembersApi,
  updateTeamApi,
  deleteTeamApi,
  removeTeamMemberApi,
  updateTeamMemberRoleApi,
  addTeamMemberApi,
  type Team,
  type TeamMember,
} from "@/lib/teams";
import { listAllUsers, type User } from "@/lib/users";

interface ExpandedTeam extends Team {
  members: TeamMember[];
}

export default function TeamsPage() {
  const user = useAppStore((state) => state.user);
  const addNotification = useAppStore((state) => state.addNotification);

  const [teams, setTeams] = useState<ExpandedTeam[]>([]);
  const [allUsers, setAllUsers] = useState<User[]>([]);
  const [loading, setLoading] = useState(true);
  const [selectedTeam, setSelectedTeam] = useState<ExpandedTeam | null>(null);

  // Edit team modal
  const [editModalOpen, setEditModalOpen] = useState(false);
  const [editName, setEditName] = useState("");
  const [editDescription, setEditDescription] = useState("");
  const [editLoading, setEditLoading] = useState(false);

  // Member management modal
  const [memberModalOpen, setMemberModalOpen] = useState(false);
  const [selectedNewMember, setSelectedNewMember] = useState<string>("");
  const [newMemberRole, setNewMemberRole] = useState<"OWNER" | "MEMBER">(
    "MEMBER",
  );
  const [memberLoading, setMemberLoading] = useState(false);

  // Role update modal
  const [roleModalOpen, setRoleModalOpen] = useState(false);
  const [selectedMember, setSelectedMember] = useState<TeamMember | null>(null);
  const [newRole, setNewRole] = useState<"OWNER" | "MEMBER">("MEMBER");
  const [roleLoading, setRoleLoading] = useState(false);

  const loadTeamsAndMembers = useCallback(async () => {
    try {
      setLoading(true);
      const teamsData = await listTeamsApi();
      const usersData = await listAllUsers();
      setAllUsers(usersData.filter((u) => u.id !== user?.id));

      // Load members for each team
      const teamsWithMembers = await Promise.all(
        teamsData.map(async (team) => {
          try {
            const members = await listTeamMembersApi(team.id);
            return { ...team, members };
          } catch {
            return { ...team, members: [] };
          }
        }),
      );

      setTeams(teamsWithMembers);
      if (teamsWithMembers.length > 0) {
        setSelectedTeam(teamsWithMembers[0]);
      }
    } catch {
      addNotification({
        message: "Failed to load teams",
        type: "warning",
      });
    } finally {
      setLoading(false);
    }
  }, [addNotification, user?.id]);

  // Load teams and users
  useEffect(() => {
    void loadTeamsAndMembers();
  }, [loadTeamsAndMembers]);

  const handleEditTeam = (team: ExpandedTeam) => {
    setSelectedTeam(team);
    setEditName(team.name);
    setEditDescription(team.description || "");
    setEditModalOpen(true);
  };

  const handleSaveTeam = async () => {
    if (!selectedTeam) return;

    try {
      setEditLoading(true);
      const updated = await updateTeamApi(selectedTeam.id, {
        name: editName.trim(),
        description: editDescription.trim(),
      });

      setTeams((prev) =>
        prev.map((t) => (t.id === selectedTeam.id ? { ...t, ...updated } : t)),
      );

      setSelectedTeam((prev) => (prev ? { ...prev, ...updated } : null));

      addNotification({
        message: "Team updated successfully",
        type: "success",
      });
      setEditModalOpen(false);
    } catch (err) {
      const errorMsg =
        err instanceof Error ? err.message : "Failed to update team";
      addNotification({
        message: errorMsg,
        type: "warning",
      });
    } finally {
      setEditLoading(false);
    }
  };

  const handleDeleteTeam = async (team: ExpandedTeam) => {
    if (
      !confirm(
        `Are you sure you want to delete "${team.name}"? This action cannot be undone.`,
      )
    ) {
      return;
    }

    try {
      await deleteTeamApi(team.id);
      setTeams((prev) => prev.filter((t) => t.id !== team.id));
      if (selectedTeam?.id === team.id) {
        setSelectedTeam(teams[0] || null);
      }
      addNotification({
        message: `Team "${team.name}" deleted successfully`,
        type: "success",
      });
    } catch (err) {
      const errorMsg =
        err instanceof Error ? err.message : "Failed to delete team";
      addNotification({
        message: errorMsg,
        type: "warning",
      });
    }
  };

  const handleAddMember = async () => {
    if (!selectedTeam || !selectedNewMember) return;

    try {
      setMemberLoading(true);
      await addTeamMemberApi(selectedTeam.id, selectedNewMember, newMemberRole);

      // Reload members
      const updatedMembers = await listTeamMembersApi(selectedTeam.id);
      setSelectedTeam((prev) =>
        prev ? { ...prev, members: updatedMembers } : null,
      );
      setTeams((prev) =>
        prev.map((t) =>
          t.id === selectedTeam.id ? { ...t, members: updatedMembers } : t,
        ),
      );

      addNotification({
        message: "Member added successfully",
        type: "success",
      });
      setMemberModalOpen(false);
      setSelectedNewMember("");
      setNewMemberRole("MEMBER");
    } catch (err) {
      const errorMsg =
        err instanceof Error ? err.message : "Failed to add member";
      addNotification({
        message: errorMsg,
        type: "warning",
      });
    } finally {
      setMemberLoading(false);
    }
  };

  const handleRemoveMember = async (member: TeamMember) => {
    if (!selectedTeam) return;

    if (!confirm(`Remove ${member.full_name} from this team?`)) {
      return;
    }

    try {
      await removeTeamMemberApi(selectedTeam.id, member.user_id);

      // Reload members
      const updatedMembers = await listTeamMembersApi(selectedTeam.id);
      setSelectedTeam((prev) =>
        prev ? { ...prev, members: updatedMembers } : null,
      );
      setTeams((prev) =>
        prev.map((t) =>
          t.id === selectedTeam.id ? { ...t, members: updatedMembers } : t,
        ),
      );

      addNotification({
        message: `${member.full_name} removed from team`,
        type: "success",
      });
    } catch (err) {
      const errorMsg =
        err instanceof Error ? err.message : "Failed to remove member";
      addNotification({
        message: errorMsg,
        type: "warning",
      });
    }
  };

  const handleUpdateMemberRole = async () => {
    if (!selectedTeam || !selectedMember) return;

    try {
      setRoleLoading(true);
      await updateTeamMemberRoleApi(
        selectedTeam.id,
        selectedMember.user_id,
        newRole,
      );

      // Reload members
      const updatedMembers = await listTeamMembersApi(selectedTeam.id);
      setSelectedTeam((prev) =>
        prev ? { ...prev, members: updatedMembers } : null,
      );
      setTeams((prev) =>
        prev.map((t) =>
          t.id === selectedTeam.id ? { ...t, members: updatedMembers } : t,
        ),
      );

      addNotification({
        message: `${selectedMember.full_name}'s role updated to ${newRole}`,
        type: "success",
      });
      setRoleModalOpen(false);
    } catch (err) {
      const errorMsg =
        err instanceof Error ? err.message : "Failed to update role";
      addNotification({
        message: errorMsg,
        type: "warning",
      });
    } finally {
      setRoleLoading(false);
    }
  };

  const isTeamOwner = selectedTeam?.members.some(
    (m) => m.user_id === user?.id && m.role === "OWNER",
  );

  // Get available users to add (not already members)
  const availableUsers = allUsers.filter(
    (u) => !selectedTeam?.members.some((m) => m.user_id === u.id),
  );

  if (loading) {
    return (
      <div className="flex h-96 items-center justify-center">
        <div className="text-center">
          <div className="mb-4 h-8 w-8 animate-spin rounded-full border-4 border-primary border-t-transparent" />
          <p className="text-sm text-text-secondary">Loading teams...</p>
        </div>
      </div>
    );
  }

  if (teams.length === 0) {
    return (
      <div className="rounded-xl border border-dashed border-border bg-card p-12 text-center">
        <Users className="mx-auto mb-3 h-12 w-12 text-text-secondary opacity-50" />
        <h3 className="mb-2 text-lg font-medium text-text-primary">
          No teams yet
        </h3>
        <p className="mb-4 text-sm text-text-secondary">
          Create your first team from the dashboard to get started.
        </p>
      </div>
    );
  }

  return (
    <div className="grid gap-6 lg:grid-cols-[300px_1fr]">
      {/* Teams List */}
      <div className="space-y-2">
        <h3 className="px-2 text-sm font-semibold text-text-primary">
          Teams ({teams.length})
        </h3>
        <div className="space-y-1">
          {teams.map((team) => (
            <button
              key={team.id}
              onClick={() => setSelectedTeam(team)}
              className={`w-full rounded-lg px-3 py-2 text-left text-sm transition-colors ${
                selectedTeam?.id === team.id
                  ? "bg-primary/20 text-primary"
                  : "text-text-secondary hover:bg-muted hover:text-text-primary"
              }`}
            >
              <div className="flex items-center justify-between">
                <div className="truncate">
                  <div className="font-medium">{team.name}</div>
                  <div className="text-xs opacity-75">
                    {team.members.length} members
                  </div>
                </div>
                <ChevronRight className="h-4 w-4 flex-shrink-0" />
              </div>
            </button>
          ))}
        </div>
      </div>

      {/* Team Details */}
      {selectedTeam && (
        <div className="space-y-6">
          {/* Team Header */}
          <div className="rounded-xl border border-border bg-card p-6">
            <div className="mb-4 flex items-start justify-between">
              <div>
                <h2 className="text-2xl font-bold text-text-primary">
                  {selectedTeam.name}
                </h2>
                {selectedTeam.description && (
                  <p className="mt-1 text-sm text-text-secondary">
                    {selectedTeam.description}
                  </p>
                )}
              </div>
              <div className="flex gap-2">
                {isTeamOwner && (
                  <>
                    <Button
                      variant="secondary"
                      size="sm"
                      onClick={() => handleEditTeam(selectedTeam)}
                    >
                      <Edit2 className="mr-2 h-4 w-4" />
                      Edit
                    </Button>
                    <Button
                      variant="destructive"
                      size="sm"
                      onClick={() => handleDeleteTeam(selectedTeam)}
                    >
                      <Trash2 className="mr-2 h-4 w-4" />
                      Delete
                    </Button>
                  </>
                )}
              </div>
            </div>

            <div className="grid grid-cols-3 gap-4 pt-4 text-sm">
              <div>
                <p className="text-text-secondary">Members</p>
                <p className="text-lg font-semibold text-text-primary">
                  {selectedTeam.members.length}
                </p>
              </div>
              <div>
                <p className="text-text-secondary">Owners</p>
                <p className="text-lg font-semibold text-text-primary">
                  {
                    selectedTeam.members.filter((m) => m.role === "OWNER")
                      .length
                  }
                </p>
              </div>
              <div>
                <p className="text-text-secondary">Created</p>
                <p className="text-lg font-semibold text-text-primary">
                  {new Date(selectedTeam.created_at).toLocaleDateString()}
                </p>
              </div>
            </div>
          </div>

          {/* Members Section */}
          <div className="rounded-xl border border-border bg-card p-6">
            <div className="mb-4 flex items-center justify-between">
              <h3 className="flex items-center gap-2 text-lg font-semibold text-text-primary">
                <Users className="h-5 w-5" />
                Team Members
              </h3>
              {isTeamOwner && availableUsers.length > 0 && (
                <Button size="sm" onClick={() => setMemberModalOpen(true)}>
                  <Plus className="mr-2 h-4 w-4" />
                  Add Member
                </Button>
              )}
            </div>

            {selectedTeam.members.length === 0 ? (
              <p className="text-sm text-text-secondary">
                No members in this team yet.
              </p>
            ) : (
              <div className="space-y-2">
                {selectedTeam.members.map((member) => (
                  <div
                    key={member.user_id}
                    className="flex items-center justify-between rounded-lg border border-border/50 p-3"
                  >
                    <div className="flex-1">
                      <p className="font-medium text-text-primary">
                        {member.full_name}
                      </p>
                      <p className="text-xs text-text-secondary">
                        {member.email}
                      </p>
                    </div>
                    <div className="flex items-center gap-2">
                      <span
                        className={`rounded-full px-3 py-1 text-xs font-medium ${
                          member.role === "OWNER"
                            ? "bg-primary/20 text-primary"
                            : "bg-muted text-text-secondary"
                        }`}
                      >
                        {member.role}
                      </span>
                      {isTeamOwner && member.user_id !== user?.id && (
                        <div className="flex gap-1">
                          <Button
                            variant="ghost"
                            size="sm"
                            onClick={() => {
                              setSelectedMember(member);
                              setNewRole(
                                member.role === "OWNER" ? "MEMBER" : "OWNER",
                              );
                              setRoleModalOpen(true);
                            }}
                          >
                            <Settings className="h-4 w-4" />
                          </Button>
                          <Button
                            variant="ghost"
                            size="sm"
                            className="text-destructive hover:bg-destructive/10 hover:text-destructive"
                            onClick={() => handleRemoveMember(member)}
                          >
                            <Trash2 className="h-4 w-4" />
                          </Button>
                        </div>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      )}

      {/* Edit Team Modal */}
      <Dialog open={editModalOpen} onOpenChange={setEditModalOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Edit Team</DialogTitle>
            <DialogDescription>
              Update team name and description
            </DialogDescription>
          </DialogHeader>

          <div className="space-y-4">
            <div>
              <Label htmlFor="team-name">Team Name *</Label>
              <Input
                id="team-name"
                value={editName}
                onChange={(e) => setEditName(e.target.value)}
                placeholder="Enter team name"
              />
            </div>
            <div>
              <Label htmlFor="team-desc">Description</Label>
              <Textarea
                id="team-desc"
                value={editDescription}
                onChange={(e) => setEditDescription(e.target.value)}
                placeholder="Enter team description"
                rows={3}
              />
            </div>
          </div>

          <DialogFooter>
            <Button
              variant="secondary"
              onClick={() => setEditModalOpen(false)}
              disabled={editLoading}
            >
              Cancel
            </Button>
            <Button
              onClick={handleSaveTeam}
              disabled={editLoading || !editName.trim()}
            >
              {editLoading ? "Saving..." : "Save Changes"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Add Member Modal */}
      <Dialog open={memberModalOpen} onOpenChange={setMemberModalOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Add Team Member</DialogTitle>
            <DialogDescription>
              Invite a user to join this team
            </DialogDescription>
          </DialogHeader>

          <div className="space-y-4">
            <div>
              <Label htmlFor="member-select">Select User *</Label>
              <Select
                value={selectedNewMember}
                onValueChange={setSelectedNewMember}
              >
                <SelectTrigger id="member-select">
                  <SelectValue placeholder="Choose a user..." />
                </SelectTrigger>
                <SelectContent>
                  {availableUsers.map((u) => (
                    <SelectItem key={u.id} value={u.id}>
                      {u.name} ({u.email})
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <div>
              <Label htmlFor="role-select">Role</Label>
              <Select
                value={newMemberRole}
                onValueChange={(v) => setNewMemberRole(v as "OWNER" | "MEMBER")}
              >
                <SelectTrigger id="role-select">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="MEMBER">Member</SelectItem>
                  <SelectItem value="OWNER">Owner</SelectItem>
                </SelectContent>
              </Select>
            </div>
          </div>

          <DialogFooter>
            <Button
              variant="secondary"
              onClick={() => setMemberModalOpen(false)}
              disabled={memberLoading}
            >
              Cancel
            </Button>
            <Button
              onClick={handleAddMember}
              disabled={memberLoading || !selectedNewMember}
            >
              {memberLoading ? "Adding..." : "Add Member"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Update Role Modal */}
      <Dialog open={roleModalOpen} onOpenChange={setRoleModalOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Update Member Role</DialogTitle>
            <DialogDescription>
              Change {selectedMember?.full_name}&apos;s role in this team
            </DialogDescription>
          </DialogHeader>

          <div className="space-y-4">
            <div>
              <Label htmlFor="new-role">New Role</Label>
              <Select
                value={newRole}
                onValueChange={(v) => setNewRole(v as "OWNER" | "MEMBER")}
              >
                <SelectTrigger id="new-role">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="MEMBER">Member</SelectItem>
                  <SelectItem value="OWNER">Owner</SelectItem>
                </SelectContent>
              </Select>
            </div>
          </div>

          <DialogFooter>
            <Button
              variant="secondary"
              onClick={() => setRoleModalOpen(false)}
              disabled={roleLoading}
            >
              Cancel
            </Button>
            <Button onClick={handleUpdateMemberRole} disabled={roleLoading}>
              {roleLoading ? "Updating..." : "Update Role"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}

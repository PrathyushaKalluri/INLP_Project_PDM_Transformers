import { api } from "./api";

export interface Workspace {
  id: string;
  name: string;
  slug: string;
  created_by: string;
  created_at: string;
}

export interface Team {
  id: string;
  name: string;
  description?: string;
  workspace_id: string;
  created_by: string;
  created_at: string;
}

export interface TeamMember {
  user_id: string;
  email: string;
  full_name: string;
  role: "OWNER" | "MEMBER";
  joined_at: string;
}

export interface TeamResponse {
  success: boolean;
  data: Team;
  message: string;
}

export interface TeamsListResponse {
  success: boolean;
  data: Team[];
  message: string;
}

/**
 * Get all workspaces for the current user
 */
export async function listWorkspacesApi(): Promise<Workspace[]> {
  try {
    const response = await api.get<Workspace[]>("/v1/workspaces");
    if (Array.isArray(response)) {
      console.log("[WorkspacesAPI] ✓ Workspaces loaded:", response.length);
      return response;
    }
    console.error("[WorkspacesAPI] Invalid response format");
    return [];
  } catch (error) {
    console.error("[WorkspacesAPI] ✗ Error fetching workspaces:", error);
    return [];
  }
}

/**
 * Get or create a default workspace for the current user.
 * Falls back when the user has no existing workspaces.
 */
export async function getOrCreateDefaultWorkspaceApi(): Promise<Workspace> {
  try {
    const response = await api.get<Workspace>("/v1/workspaces/default");
    if (response && typeof response === "object") {
      console.log("[WorkspacesAPI] ✓ Default workspace:", response.name);
      return response;
    }
    throw new Error("Invalid workspace response");
  } catch (error) {
    console.error("[WorkspacesAPI] ✗ Error getting default workspace:", error);
    throw error;
  }
}

/**
 * Get all teams for the current user
 */
export async function listTeamsApi(): Promise<Team[]> {
  console.log("[TeamsAPI] Fetching teams");

  try {
    // Use /v1 prefix for v1 API routes
    const response = await api.get<Team[]>("/v1/teams");
    // Backend returns array directly
    if (Array.isArray(response)) {
      console.log("[TeamsAPI] ✓ Teams loaded:", response.length);
      return response;
    }
    console.error("[TeamsAPI] ✗ Invalid response format");
    throw new Error("Invalid response format from teams endpoint");
  } catch (error) {
    console.error("[TeamsAPI] ✗ Error fetching teams:", error);
    throw error;
  }
}

/**
 * Get a specific team by ID
 */
export async function getTeamApi(teamId: string): Promise<Team> {
  console.log("[TeamsAPI] Getting team:", teamId);

  try {
    const response = await api.get<Team>(`/v1/teams/${teamId}`);
    if (!response || typeof response !== "object") {
      throw new Error("Invalid response format from team endpoint");
    }
    console.log("[TeamsAPI] ✓ Team loaded:", response.name);
    return response;
  } catch (error) {
    console.error(`[TeamsAPI] ✗ Error fetching team ${teamId}:`, error);
    throw error;
  }
}

/**
 * Create a new team in a workspace
 */
export async function createTeamApi(
  workspaceId: string,
  data: {
    name: string;
    description?: string;
  },
): Promise<Team> {
  console.log("[TeamsAPI] Creating team:", { workspaceId, name: data.name });

  try {
    const response = await api.post<Team>(
      `/v1/workspaces/${workspaceId}/teams`,
      data,
    );
    console.log("[TeamsAPI] ✓ Team created:", response.name);
    return response;
  } catch (error) {
    console.error("[TeamsAPI] ✗ Error creating team:", error);
    throw error;
  }
}

/**
 * Update a team
 */
export async function updateTeamApi(
  teamId: string,
  data: { name?: string; description?: string },
): Promise<Team> {
  try {
    const response = await api.patch<Team>(`/v1/teams/${teamId}`, data);
    if (!response || typeof response !== "object") {
      throw new Error("Invalid response format from update team endpoint");
    }
    return response;
  } catch (error) {
    console.error(`Error updating team ${teamId}:`, error);
    throw error;
  }
}

/**
 * Delete a team
 */
export async function deleteTeamApi(teamId: string): Promise<void> {
  try {
    await api.delete(`/v1/teams/${teamId}`);
  } catch (error) {
    console.error(`Error deleting team ${teamId}:`, error);
    throw error;
  }
}

/**
 * Add a member to a team
 */
export async function addTeamMemberApi(
  teamId: string,
  userId: string,
  role: string,
): Promise<void> {
  try {
    await api.post(`/v1/teams/${teamId}/members`, { user_id: userId, role });
  } catch (error) {
    console.error(`Error adding member to team ${teamId}:`, error);
    throw error;
  }
}

/**
 * Remove a member from a team
 */
export async function removeTeamMemberApi(
  teamId: string,
  userId: string,
): Promise<void> {
  try {
    await api.delete(`/v1/teams/${teamId}/members/${userId}`);
  } catch (error) {
    console.error(`Error removing member from team ${teamId}:`, error);
    throw error;
  }
}

/**
 * List team members with details
 */
export async function listTeamMembersApi(
  teamId: string,
): Promise<TeamMember[]> {
  try {
    const response = await api.get<TeamMember[]>(`/v1/teams/${teamId}/members`);
    if (Array.isArray(response)) {
      return response;
    }
    throw new Error("Invalid response format");
  } catch (error) {
    console.error(`Error fetching team members:`, error);
    throw error;
  }
}

/**
 * Update a team member's role
 */
export async function updateTeamMemberRoleApi(
  teamId: string,
  userId: string,
  role: "OWNER" | "MEMBER",
): Promise<void> {
  try {
    await api.patch(`/teams/${teamId}/members/${userId}`, { role });
  } catch (error) {
    console.error(`Error updating member role:`, error);
    throw error;
  }
}

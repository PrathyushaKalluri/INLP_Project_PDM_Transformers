/**
 * Projects API client
 */

import { api } from "./api";
import { Project } from "@/types";

interface BackendProject {
  id: string;
  team_id?: string;
  teamId?: string; // Backend returns camelCase
  owner_id?: string;
  ownerId?: string; // Backend returns camelCase
  name: string;
  description: string | null;
  members?: Array<{ user_id: string; joined_at: string }>;
  participantIds?: string[]; // Backend returns camelCase
  is_archived?: boolean;
  isArchived?: boolean; // Backend returns camelCase
  created_by?: string;
  createdBy?: string; // Backend returns camelCase
  created_at?: string;
  createdAt?: string; // Backend returns camelCase
  updated_at?: string;
  updatedAt?: string; // Backend returns camelCase
}

interface BackendProjectMember {
  user_id: string;
  joined_at: string;
}

/**
 * Convert backend project to frontend type
 * Handles both snake_case (internal API) and camelCase (frontend responses)
 */
function mapProject(data: BackendProject): Project {
  // Handle both camelCase and snake_case field names
  const participants =
    data.participantIds ||
    (data.members ? data.members.map((m) => m.user_id) : []);

  return {
    id: data.id,
    teamId: data.teamId || data.team_id,
    name: data.name,
    description: data.description || "",
    participants: participants,
  };
}

/**
 * List projects for current user
 */
export async function listProjects(
  page = 1,
  limit = 50,
): Promise<{
  projects: Project[];
  total: number;
  page: number;
}> {
  console.log("[ProjectsAPI] Listing projects:", { page, limit });

  try {
    // Use /frontend prefix for frontend adapter routes
    const response = await api.get<{
      items: BackendProject[];
      total: number;
      page: number;
    }>(`/frontend/projects?page=${page}&limit=${limit}`);

    console.log("[ProjectsAPI] ✓ Projects loaded:", {
      count: response.items?.length || 0,
      total: response.total,
    });

    return {
      projects: (response.items || []).map(mapProject),
      total: response.total || 0,
      page: response.page || 1,
    };
  } catch (error) {
    console.error("[ProjectsAPI] ✗ Failed to list projects:", error);
    throw error;
  }
}

/**
 * Get single project by ID
 */
export async function getProject(projectId: string): Promise<Project> {
  console.log("[ProjectsAPI] Getting project:", projectId);

  try {
    const data = await api.get<BackendProject>(
      `/frontend/projects/${projectId}`,
    );
    console.log("[ProjectsAPI] ✓ Project loaded:", data);
    return mapProject(data);
  } catch (error) {
    console.error("[ProjectsAPI] ✗ Failed to get project:", projectId, error);
    throw error;
  }
}

/**
 * Create a new project
 */
export async function createProject(input: {
  team_id: string;
  name: string;
  description?: string;
}): Promise<Project> {
  console.log("[ProjectsAPI] Creating project:", {
    teamId: input.team_id,
    name: input.name,
    description: input.description?.substring(0, 50),
  });

  try {
    // Use /frontend prefix and camelCase field names via pydantic aliases
    const response = await api.post<BackendProject>("/frontend/projects", {
      teamId: input.team_id,
      name: input.name,
      description: input.description,
    });

    console.log("[ProjectsAPI] ✓ Project created:", {
      id: response.id,
      name: response.name,
    });
    return mapProject(response);
  } catch (error) {
    console.error("[ProjectsAPI] ✗ Failed to create project:", {
      input,
      error,
    });
    throw error;
  }
}

/**
 * Update project
 */
export async function updateProject(
  projectId: string,
  updates: {
    name?: string;
    description?: string;
    is_archived?: boolean;
  },
): Promise<Project> {
  console.log("[ProjectsAPI] Updating project:", { projectId, updates });

  try {
    const data = await api.patch<BackendProject>(
      `/frontend/projects/${projectId}`,
      updates,
    );
    console.log("[ProjectsAPI] ✓ Project updated:", data);
    return mapProject(data);
  } catch (error) {
    console.error("[ProjectsAPI] ✗ Failed to update project:", {
      projectId,
      error,
    });
    throw error;
  }
}

/**
 * Delete project
 */
export async function deleteProject(projectId: string): Promise<void> {
  console.log("[ProjectsAPI] Deleting project:", projectId);

  try {
    await api.delete(`/frontend/projects/${projectId}`);
    console.log("[ProjectsAPI] ✓ Project deleted");
  } catch (error) {
    console.error(
      "[ProjectsAPI] ✗ Failed to delete project:",
      projectId,
      error,
    );
    throw error;
  }
}

/**
 * Get project members
 */
export async function listProjectMembers(
  projectId: string,
): Promise<BackendProjectMember[]> {
  console.log("[ProjectsAPI] Loading project members:", projectId);

  try {
    const members = await api.get(`/frontend/projects/${projectId}/members`);
    console.log(
      "[ProjectsAPI] ✓ Members loaded:",
      Array.isArray(members) ? members.length : 0,
    );
    return Array.isArray(members) ? members : [];
  } catch (error) {
    console.error("[ProjectsAPI] ✗ Failed to load members:", projectId, error);
    throw error;
  }
}

/**
 * Add member to project
 */
export async function addProjectMember(
  projectId: string,
  userId: string,
): Promise<void> {
  console.log("[ProjectsAPI] Adding member to project:", {
    projectId,
    userId,
  });

  try {
    // Use /frontend prefix and camelCase field name
    await api.post(`/frontend/projects/${projectId}/participants`, { userId });
    console.log("[ProjectsAPI] ✓ Member added successfully");
  } catch (error) {
    const message = error instanceof Error ? error.message : String(error);
    console.error("[ProjectAPI] ✗ Failed to add member:", message);
    throw error;
  }
}

/**
 * Remove member from project
 */
export async function removeProjectMember(
  projectId: string,
  userId: string,
): Promise<void> {
  await api.delete(`/projects/${projectId}/members/${userId}`);
}

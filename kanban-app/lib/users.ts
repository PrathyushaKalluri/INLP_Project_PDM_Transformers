/**
 * Users API client
 */

import { api } from "./api";
import { User } from "@/types";

// Re-export for easier imports
export type { User };

interface BackendUser {
  id: string;
  email: string;
  full_name: string;
  role: string;
  is_active: boolean;
  created_at: string;
}

// Seed data for users - matches backend seed.py
// These are the real users from backend database
const SEED_USERS: BackendUser[] = [
  {
    id: "admin-001",
    email: "admin@acme.com",
    full_name: "Admin User",
    role: "admin",
    is_active: true,
    created_at: new Date().toISOString(),
  },
  {
    id: "alice-001",
    email: "alice@acme.com",
    full_name: "Alice Chen",
    role: "manager",
    is_active: true,
    created_at: new Date().toISOString(),
  },
  {
    id: "bob-001",
    email: "bob@acme.com",
    full_name: "Bob Smith",
    role: "member",
    is_active: true,
    created_at: new Date().toISOString(),
  },
  {
    id: "carol-001",
    email: "carol@acme.com",
    full_name: "Carol Davis",
    role: "member",
    is_active: true,
    created_at: new Date().toISOString(),
  },
  {
    id: "dave-001",
    email: "dave@acme.com",
    full_name: "Dave Wilson",
    role: "member",
    is_active: true,
    created_at: new Date().toISOString(),
  },
];

// Check if seed data mode is enabled
function isUsingSeedData(): boolean {
  if (typeof window === "undefined") return false;
  return localStorage.getItem("useSeedData") === "true";
}

// Toggle seed data mode
export function toggleSeedDataMode(): boolean {
  if (typeof window === "undefined") return false;
  const current = isUsingSeedData();
  const newValue = !current;
  localStorage.setItem("useSeedData", String(newValue));
  console.log(`[UsersAPI] Seed data mode: ${newValue}`);
  return newValue;
}

// Get current seed data mode status
export function getSeedDataMode(): boolean {
  return isUsingSeedData();
}

/**
 * Convert backend user to frontend type
 */
function mapUser(data: BackendUser): User {
  return {
    id: data.id,
    name: data.full_name,
    email: data.email,
    role: data.role as "manager" | "member",
    avatar: data.full_name
      .split(" ")
      .map((n) => n[0])
      .join("")
      .toUpperCase()
      .slice(0, 2),
  };
}

/**
 * Search for users by email
 */
export async function searchUsersByEmail(email: string): Promise<User[]> {
  if (isUsingSeedData()) {
    console.log(`[UsersAPI] Using seed data for search: ${email}`);
    const filtered = SEED_USERS.filter((u) =>
      u.email.toLowerCase().includes(email.toLowerCase()),
    );
    return filtered.map(mapUser);
  }

  try {
    const response = await api.get<BackendUser[]>(`/users?email=${email}`);
    return response.map(mapUser);
  } catch (error) {
    console.error(
      `[UsersAPI] Error searching users, falling back to seed:`,
      error,
    );
    const filtered = SEED_USERS.filter((u) =>
      u.email.toLowerCase().includes(email.toLowerCase()),
    );
    return filtered.map(mapUser);
  }
}

/**
 * Get all users (workspace members)
 * Uses seed data by default, falls back to API if user explicitly enables it
 */
export async function listAllUsers(): Promise<User[]> {
  if (isUsingSeedData()) {
    console.log(
      `[UsersAPI] Returning seed users - ${SEED_USERS.length} available users from Acme Corp`,
    );
    return SEED_USERS.map(mapUser);
  }

  try {
    const response = await api.get<BackendUser[]>("/v1/users");
    if (Array.isArray(response)) {
      return response.map(mapUser);
    }
  } catch (error) {
    console.error(
      "[UsersAPI] Error listing users from backend, falling back to seed:",
      error,
    );
  }

  return SEED_USERS.map(mapUser);
}

/**
 * Get user by ID
 */
export async function getUserById(userId: string): Promise<User> {
  if (isUsingSeedData()) {
    console.log(`[UsersAPI] Using seed data for user: ${userId}`);
    const user = SEED_USERS.find((u) => u.id === userId);
    if (!user) {
      throw new Error(`User ${userId} not found in seed data`);
    }
    return mapUser(user);
  }

  try {
    const data = await api.get<BackendUser>(`/users/${userId}`);
    return mapUser(data);
  } catch (error) {
    console.error(
      `[UsersAPI] Error fetching user ${userId}, falling back to seed:`,
      error,
    );
    const user = SEED_USERS.find((u) => u.id === userId);
    if (!user) {
      throw new Error(`User ${userId} not found`);
    }
    return mapUser(user);
  }
}

/**
 * Update current user profile
 */
export async function updateCurrentUser(updates: {
  full_name?: string;
  password?: string;
}): Promise<User> {
  const data = await api.patch<BackendUser>("/users/me", updates);
  return mapUser(data);
}

import { z } from "zod";

import { apiClient, clearAuthToken, parseWithSchema, setAuthToken } from "@/lib/api/client";
import type { User } from "@/types";

const roleSchema = z.enum(["manager", "member"]);

const userSchema = z.object({
  id: z.string(),
  name: z.string(),
  email: z.string().email(),
  role: roleSchema,
  avatar: z.string(),
});

const authResponseSchema = z.object({
  user: userSchema,
  token: z.string().optional(),
});

const loginPayloadSchema = z.object({
  email: z.string().email(),
  password: z.string().min(1),
});

const signupPayloadSchema = z.object({
  email: z.string().email(),
  password: z.string().min(6),
  name: z.string().min(1).optional(),
});

const forgotPasswordPayloadSchema = z.object({
  email: z.string().email(),
});

type LoginPayload = z.infer<typeof loginPayloadSchema>;
type SignupPayload = z.infer<typeof signupPayloadSchema>;

const persistTokenFromAuth = (token?: string) => {
  if (token) {
    setAuthToken(token);
  }
};

export async function login(payload: LoginPayload): Promise<User> {
  const body = loginPayloadSchema.parse(payload);
  const response = await apiClient.post("/auth/login", body);
  const parsed = parseWithSchema(authResponseSchema, response.data, "Invalid login response");
  persistTokenFromAuth(parsed.token);
  return parsed.user;
}

export async function signup(payload: SignupPayload): Promise<User> {
  const body = signupPayloadSchema.parse(payload);
  const response = await apiClient.post("/auth/signup", body);
  const parsed = parseWithSchema(authResponseSchema, response.data, "Invalid signup response");
  persistTokenFromAuth(parsed.token);
  return parsed.user;
}

export async function forgotPassword(payload: { email: string }) {
  const body = forgotPasswordPayloadSchema.parse(payload);
  await apiClient.post("/auth/forgot-password", body);
}

export async function logout() {
  try {
    await apiClient.post("/auth/logout");
  } finally {
    clearAuthToken();
  }
}

export async function getCurrentUser(): Promise<User> {
  const response = await apiClient.get("/auth/me");
  const parsed = parseWithSchema(userSchema, response.data, "Invalid current user response");
  return parsed;
}

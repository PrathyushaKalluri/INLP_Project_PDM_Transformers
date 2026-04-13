/**
 * Auth API methods - signup, login, refresh, get me
 */

import { api, TokenPair, setTokens, clearTokens } from "./api";
import { User } from "@/types";

export interface SignupRequest {
  email: string;
  password: string;
  full_name: string;
  role: "manager" | "member";
}

export interface LoginRequest {
  email: string;
  password: string;
}

export interface RefreshRequest {
  refresh_token: string;
}

interface UserResponse {
  id: string;
  email: string;
  full_name: string;
  role: string;
  is_active: boolean;
  created_at: string;
}

/**
 * Convert backend UserResponse to frontend User type
 */
function mapUserResponse(data: UserResponse): User {
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
 * Sign up with email, password, name, and role
 * Optimized: Uses login response to get user data in single call
 */
export async function signup(data: SignupRequest): Promise<{
  user: User;
  tokens: TokenPair;
}> {
  const startTime = performance.now();
  console.debug(`[FRONTEND_AUTH] Signup start for ${data.email}`);

  try {
    const registerStart = performance.now();
    console.debug(`[FRONTEND_AUTH] Sending POST /v1/auth/register`);
    await api.post<UserResponse>("/v1/auth/register", data);
    const registerTime = performance.now() - registerStart;
    console.debug(
      `[FRONTEND_AUTH] Register response received - ${registerTime.toFixed(2)}ms`,
    );

    // After registration, login to get tokens and ensure user is created
    const loginStart = performance.now();
    console.debug(`[FRONTEND_AUTH] Sending POST /v1/auth/login after register`);
    const loginResponse = await api.post<{
      access_token: string;
      refresh_token: string;
      token_type: string;
      user: UserResponse;
    }>("/v1/auth/login", {
      email: data.email,
      password: data.password,
    });
    const loginTime = performance.now() - loginStart;
    console.debug(
      `[FRONTEND_AUTH] Login response received - ${loginTime.toFixed(2)}ms`,
    );

    setTokens({
      access_token: loginResponse.access_token,
      refresh_token: loginResponse.refresh_token,
      token_type: loginResponse.token_type,
    });

    const totalTime = performance.now() - startTime;
    console.debug(
      `[FRONTEND_AUTH] Signup complete for ${data.email} - Total: ${totalTime.toFixed(2)}ms (Register: ${registerTime.toFixed(2)}ms, Login: ${loginTime.toFixed(2)}ms)`,
    );

    return {
      user: mapUserResponse(loginResponse.user),
      tokens: {
        access_token: loginResponse.access_token,
        refresh_token: loginResponse.refresh_token,
        token_type: loginResponse.token_type,
      },
    };
  } catch (error) {
    const totalTime = performance.now() - startTime;
    console.error(
      `[FRONTEND_AUTH] Signup failed for ${data.email} - ${totalTime.toFixed(2)}ms - Error: ${error instanceof Error ? error.message : String(error)}`,
    );
    throw error;
  }
}

/**
 * Login with email and password
 * Returns tokens (access + refresh) and user data in single response
 */
export async function login(
  credentials: LoginRequest,
): Promise<{ user: User; tokens: TokenPair }> {
  const startTime = performance.now();
  console.debug(`[FRONTEND_AUTH] Login start for ${credentials.email}`);

  try {
    const requestStart = performance.now();
    console.debug(`[FRONTEND_AUTH] Sending POST /v1/auth/login`);

    const response = await api.post<{
      access_token: string;
      refresh_token: string;
      token_type: string;
      user: UserResponse;
    }>("/v1/auth/login", credentials);

    const requestTime = performance.now() - requestStart;
    console.debug(
      `[FRONTEND_AUTH] API response received - ${requestTime.toFixed(2)}ms`,
    );

    const setTokensStart = performance.now();
    setTokens({
      access_token: response.access_token,
      refresh_token: response.refresh_token,
      token_type: response.token_type,
    });
    const setTokensTime = performance.now() - setTokensStart;
    console.debug(`[FRONTEND_AUTH] Tokens set - ${setTokensTime.toFixed(2)}ms`);

    const mapUserStart = performance.now();
    const mappedUser = mapUserResponse(response.user);
    const mapUserTime = performance.now() - mapUserStart;
    console.debug(`[FRONTEND_AUTH] User mapped - ${mapUserTime.toFixed(2)}ms`);

    const totalTime = performance.now() - startTime;
    console.debug(
      `[FRONTEND_AUTH] Login complete for ${credentials.email} - Total: ${totalTime.toFixed(2)}ms (Request: ${requestTime.toFixed(2)}ms, SetTokens: ${setTokensTime.toFixed(2)}ms, MapUser: ${mapUserTime.toFixed(2)}ms)`,
    );

    return {
      user: mappedUser,
      tokens: {
        access_token: response.access_token,
        refresh_token: response.refresh_token,
        token_type: response.token_type,
      },
    };
  } catch (error) {
    const totalTime = performance.now() - startTime;
    console.error(
      `[FRONTEND_AUTH] Login failed for ${credentials.email} - ${totalTime.toFixed(2)}ms - Error: ${error instanceof Error ? error.message : String(error)}`,
    );
    throw error;
  }
}

/**
 * Get current authenticated user
 */
export async function getMe(): Promise<User> {
  const data = await api.get<UserResponse>("/v1/auth/me");
  return mapUserResponse(data);
}

/**
 * Refresh access token
 */
export async function refreshToken(refreshToken: string): Promise<TokenPair> {
  const tokens = await api.post<TokenPair>("/v1/auth/refresh", {
    refresh_token: refreshToken,
  });
  setTokens(tokens);
  return tokens;
}

/**
 * Logout - clear stored tokens
 */
export function logout(): void {
  clearTokens();
}

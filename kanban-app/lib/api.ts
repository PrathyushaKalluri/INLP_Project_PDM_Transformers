/**
 * HTTP API Client with automatic JWT token management
 * Handles:
 * - Token storage/retrieval from localStorage
 * - Authorization headers
 * - Token refresh on 401
 * - Support for both /api/v1 and /api/frontend prefixes
 * - Request timeouts (adaptive by endpoint)
 */

// Note: Base URL is just /api, not /api/v1
// Callers should specify full path: /v1/teams or /frontend/projects
function normalizeApiRoot(value: string): string {
  return value.replace(/\/$/, "");
}

function resolveApiBase(): string {
  const apiEndpoint = process.env.NEXT_PUBLIC_API_ENDPOINT?.trim();
  if (apiEndpoint) {
    return normalizeApiRoot(apiEndpoint);
  }

  const apiBase = process.env.NEXT_PUBLIC_API_BASE?.trim();
  if (apiBase) {
    return normalizeApiRoot(apiBase);
  }

  const apiBaseUrl = process.env.NEXT_PUBLIC_API_BASE_URL?.trim();
  if (apiBaseUrl) {
    const normalized = normalizeApiRoot(apiBaseUrl);
    return normalized.endsWith("/api") ? normalized : `${normalized}/api`;
  }

  return process.env.NODE_ENV === "development"
    ? "http://localhost:8000/api"
    : "/api";
}

const API_BASE = resolveApiBase();

// Fallback used only for auth timeouts to keep login responsive if a stale
// local process occupies :8000 while backend is running on an alternate port.
const AUTH_FALLBACK_BASE =
  process.env.NEXT_PUBLIC_API_FALLBACK_BASE?.replace(/\/$/, "") ||
  (process.env.NODE_ENV === "development"
    ? "http://127.0.0.1:8010/api"
    : "/api");
// Request timeout constants tuned by endpoint type
const DEFAULT_REQUEST_TIMEOUT = 15000; // 15 seconds - standard endpoints
const AUTH_REQUEST_TIMEOUT = 60000; // 60 seconds - auth flows can cold-start on the first request
const PROJECT_REQUEST_TIMEOUT = 30000; // 30 seconds - project CRUD operations
const TEAM_REQUEST_TIMEOUT = 30000; // 30 seconds - team/workspace list operations with pagination/search
const NLP_PIPELINE_TIMEOUT = 60000; // 60 seconds - NLP processing endpoints (cold-start of models on first publish/process)
const AUTH_RETRY_DELAY_MS = 750;

// Route request to appropriate timeout tier based on endpoint path
// This prevents timeouts on long-running NLP operations while keeping auth responsive
function getRequestTimeout(endpoint: string): number {
  if (
    endpoint === "/v1/auth/login" ||
    endpoint === "/v1/auth/register" ||
    endpoint === "/v1/auth/refresh"
  ) {
    return AUTH_REQUEST_TIMEOUT;
  }

  if (
    endpoint === "/frontend/projects" ||
    endpoint.startsWith("/frontend/projects/") ||
    endpoint === "/v1/projects" ||
    endpoint.startsWith("/v1/projects/")
  ) {
    return PROJECT_REQUEST_TIMEOUT;
  }

  if (
    endpoint === "/v1/teams" ||
    endpoint.startsWith("/v1/teams/") ||
    endpoint === "/v1/workspaces" ||
    endpoint.startsWith("/v1/workspaces/")
  ) {
    return TEAM_REQUEST_TIMEOUT;
  }

  // NLP pipeline endpoints (publish, process) need longer timeout for model loading
  if (endpoint === "/frontend/publish" || endpoint === "/frontend/process") {
    return NLP_PIPELINE_TIMEOUT;
  }

  return DEFAULT_REQUEST_TIMEOUT;
}

export interface TokenPair {
  access_token: string;
  refresh_token: string;
  token_type: string;
}

const TOKEN_STORAGE_KEY = "kanban_auth_token";
const REFRESH_TOKEN_STORAGE_KEY = "kanban_refresh_token";

/**
 * Get current access token from storage
 */
export function getAccessToken(): string | null {
  if (typeof window === "undefined") return null;
  const token = window.localStorage.getItem(TOKEN_STORAGE_KEY);
  if (!token || token === "undefined" || token === "null") return null;
  return token;
}

/**
 * Get refresh token from storage
 */
export function getRefreshToken(): string | null {
  if (typeof window === "undefined") return null;
  const token = window.localStorage.getItem(REFRESH_TOKEN_STORAGE_KEY);
  if (!token || token === "undefined" || token === "null") return null;
  return token;
}

/**
 * Store tokens in localStorage
 */
export function setTokens(tokens: TokenPair): void {
  if (typeof window === "undefined") return;
  if (!tokens.access_token || !tokens.refresh_token) {
    clearTokens();
    return;
  }
  window.localStorage.setItem(TOKEN_STORAGE_KEY, tokens.access_token);
  window.localStorage.setItem(REFRESH_TOKEN_STORAGE_KEY, tokens.refresh_token);
}

/**
 * Clear tokens from localStorage
 */
export function clearTokens(): void {
  if (typeof window === "undefined") return;
  window.localStorage.removeItem(TOKEN_STORAGE_KEY);
  window.localStorage.removeItem(REFRESH_TOKEN_STORAGE_KEY);
}

/**
 * Refresh access token using refresh token
 */
async function refreshAccessToken(): Promise<TokenPair | null> {
  const refreshToken = getRefreshToken();
  if (!refreshToken) return null;

  const refreshEndpoints = [
    `${API_BASE}/v1/auth/refresh`,
    `${API_BASE}/frontend/auth/refresh`,
  ];

  const payloads = [{ refresh_token: refreshToken }, { refreshToken }];

  try {
    for (const url of refreshEndpoints) {
      for (const payload of payloads) {
        const response = await fetch(url, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(payload),
        });

        if (!response.ok) {
          continue;
        }

        const data = (await response.json()) as
          | TokenPair
          | { token?: string; refreshToken?: string; token_type?: string };

        const normalized: TokenPair = {
          access_token:
            (data as TokenPair).access_token ||
            (data as { token?: string }).token ||
            "",
          refresh_token:
            (data as TokenPair).refresh_token ||
            (data as { refreshToken?: string }).refreshToken ||
            "",
          token_type: (data as TokenPair).token_type || "bearer",
        };

        if (!normalized.access_token || !normalized.refresh_token) {
          continue;
        }

        setTokens(normalized);
        return normalized;
      }
    }
  } catch (error) {
    console.error("Token refresh failed:", error);
  }

  return null;
}

/**
 * Core fetch wrapper with auth + error handling + timeout
 *
 * Endpoint should include full path:
 * - "/v1/teams" → http://localhost:8000/api/v1/teams
 * - "/frontend/projects" → http://localhost:8000/api/frontend/projects
 */
export async function apiCall<T>(
  endpoint: string,
  options: RequestInit = {},
): Promise<T> {
  return apiCallWithRetry<T>(endpoint, options, 0);
}

async function apiCallWithRetry<T>(
  endpoint: string,
  options: RequestInit = {},
  retryCount: number,
): Promise<T> {
  const requestId = Math.random().toString(36).slice(2, 9);
  const startTime = performance.now();
  const url = `${API_BASE}${endpoint}`;
  const { headers: customHeaders = {}, ...restOptions } = options;

  const accessToken = getAccessToken();
  const isDev = process.env.NODE_ENV === "development";

  const headers: HeadersInit = {
    "Content-Type": "application/json",
    ...customHeaders,
    ...(accessToken && { Authorization: `Bearer ${accessToken}` }),
  };

  const method = (options.method || "GET").toUpperCase();
  const requestTimeout = getRequestTimeout(endpoint);

  console.debug(`[API_${requestId}] START ${method} ${endpoint}`);

  if (isDev) {
    const bodyStr = (restOptions as Record<string, unknown>).body;
    console.log(`[API_${requestId}] ${method} ${endpoint}`, {
      url,
      hasToken: !!accessToken,
      body: typeof bodyStr === "string" ? JSON.parse(bodyStr) : undefined,
    });
  }

  // Create AbortController for timeout
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), requestTimeout);

  const readJsonOrEmpty = async <R>(
    response: Response,
  ): Promise<R | undefined> => {
    const contentLength = response.headers.get("content-length");
    const contentType = response.headers.get("content-type") || "";

    if (response.status === 204 || contentLength === "0") {
      return undefined;
    }

    if (!contentType.includes("application/json")) {
      const text = await response.text();
      if (!text.trim()) {
        return undefined;
      }
      try {
        return JSON.parse(text) as R;
      } catch {
        return undefined;
      }
    }

    const text = await response.text();
    if (!text.trim()) {
      return undefined;
    }
    return JSON.parse(text) as R;
  };

  try {
    const fetchStart = performance.now();
    console.debug(`[API_${requestId}] Sending fetch request...`);

    let response = await fetch(url, {
      ...restOptions,
      headers,
      signal: controller.signal,
    });

    const fetchTime = performance.now() - fetchStart;
    console.debug(
      `[API_${requestId}] Response received - ${fetchTime.toFixed(2)}ms (status: ${response.status})`,
    );

    // If 401, attempt token refresh
    if (response.status === 401 && accessToken) {
      console.debug(
        `[API_${requestId}] 401 Unauthorized - attempting token refresh`,
      );
      if (isDev)
        console.log("[API] ⚠️ 401 Unauthorized - attempting token refresh");
      const newTokens = await refreshAccessToken();
      if (newTokens) {
        // Retry request with new token
        const freshHeaders: HeadersInit = {
          "Content-Type": "application/json",
          ...customHeaders,
          Authorization: `Bearer ${newTokens.access_token}`,
        };

        console.debug(`[API_${requestId}] Retrying with refreshed token...`);
        response = await fetch(url, {
          ...restOptions,
          headers: freshHeaders,
          signal: controller.signal,
        });
        console.debug(
          `[API_${requestId}] Retry response received - status: ${response.status}`,
        );
        if (isDev) console.log("[API] ✓ Token refreshed, retrying request");
      } else {
        clearTokens();
      }
    }

    // Handle non-OK responses
    if (!response.ok) {
      const errorData =
        (await readJsonOrEmpty<Record<string, unknown>>(response)) || {};
      const errorDetail =
        typeof errorData.detail === "string" ? errorData.detail : undefined;
      const errorMessageField =
        typeof errorData.message === "string" ? errorData.message : undefined;
      const errorMessage =
        errorDetail ||
        errorMessageField ||
        `HTTP ${response.status}: ${response.statusText}`;

      const totalTime = performance.now() - startTime;
      console.debug(
        `[API_${requestId}] ERROR - ${errorMessage} (${totalTime.toFixed(2)}ms)`,
      );

      if (isDev) {
        console.error(`[API_${requestId}] ✗ ${method} ${endpoint} failed:`, {
          status: response.status,
          message: errorMessage,
          data: errorData,
        });
      }

      const error = new Error(errorMessage) as Error & {
        status?: number;
        data?: unknown;
      };
      error.status = response.status;
      error.data = errorData;
      throw error;
    }

    // Parse JSON response
    const parseStart = performance.now();
    const data = await readJsonOrEmpty<T>(response);
    const parseTime = performance.now() - parseStart;

    const totalTime = performance.now() - startTime;
    console.debug(
      `[API_${requestId}] SUCCESS - Total: ${totalTime.toFixed(2)}ms (Parse: ${parseTime.toFixed(2)}ms)`,
    );

    if (isDev) {
      console.log(`[API_${requestId}] ✓ ${method} ${endpoint}`, {
        status: response.status,
        totalTime: totalTime.toFixed(2) + "ms",
        dataKeys:
          data && typeof data === "object"
            ? Object.keys(data).slice(0, 5)
            : typeof data,
      });
    }

    return data as T;
  } catch (error) {
    const isAuthEndpoint =
      endpoint === "/v1/auth/login" || endpoint === "/v1/auth/refresh";
    const shouldTryFallback =
      isAuthEndpoint &&
      error instanceof Error &&
      (error.message.includes("timeout") ||
        error.message.includes("Failed to fetch")) &&
      AUTH_FALLBACK_BASE !== API_BASE;

    if (shouldTryFallback) {
      try {
        const fallbackUrl = `${AUTH_FALLBACK_BASE}${endpoint}`;
        const fallbackResponse = await fetch(fallbackUrl, {
          ...restOptions,
          headers,
        });

        if (fallbackResponse.ok) {
          const fallbackData = (await fallbackResponse.json()) as T;
          return fallbackData;
        }
      } catch {
        // Ignore fallback errors and return original error below.
      }
    }

    const totalTime = performance.now() - startTime;
    if (error instanceof Error && error.name === "AbortError") {
      const timeoutError = new Error(
        `Request timeout after ${requestTimeout}ms: ${method} ${endpoint}`,
      );
      console.error(`[API_${requestId}] TIMEOUT - ${totalTime.toFixed(2)}ms`);
      throw timeoutError;
    }
    console.error(
      `[API_${requestId}] ERROR - ${error instanceof Error ? error.message : String(error)} (${totalTime.toFixed(2)}ms)`,
    );
    const isRetryableAuthError =
      isAuthEndpoint &&
      retryCount === 0 &&
      error instanceof Error &&
      (error.name === "AbortError" ||
        error.message.includes("timeout") ||
        error.message.includes("Failed to fetch"));

    if (isRetryableAuthError) {
      console.warn(
        `[API_${requestId}] Auth request failed on first attempt; retrying once after ${AUTH_RETRY_DELAY_MS}ms`,
      );
      await new Promise((resolve) => setTimeout(resolve, AUTH_RETRY_DELAY_MS));
      return apiCallWithRetry<T>(endpoint, options, retryCount + 1);
    }

    throw error;
  } finally {
    clearTimeout(timeout);
  }
}

/**
 * Convenience methods for common HTTP verbs
 */
export const api = {
  get: <T>(endpoint: string, options?: RequestInit) =>
    apiCall<T>(endpoint, { ...options, method: "GET" }),

  post: <T>(endpoint: string, body?: unknown, options?: RequestInit) =>
    apiCall<T>(endpoint, {
      ...options,
      method: "POST",
      body: body ? JSON.stringify(body) : undefined,
    }),

  patch: <T>(endpoint: string, body?: unknown, options?: RequestInit) =>
    apiCall<T>(endpoint, {
      ...options,
      method: "PATCH",
      body: body ? JSON.stringify(body) : undefined,
    }),

  delete: <T = void>(endpoint: string, options?: RequestInit) =>
    apiCall<T>(endpoint, { ...options, method: "DELETE" }),

  put: <T>(endpoint: string, body?: unknown, options?: RequestInit) =>
    apiCall<T>(endpoint, {
      ...options,
      method: "PUT",
      body: body ? JSON.stringify(body) : undefined,
    }),
};

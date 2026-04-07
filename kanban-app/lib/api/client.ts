import axios from "axios";
import { z } from "zod";

const AUTH_TOKEN_STORAGE_KEY = "kanban-auth-token";

export class ApiError extends Error {
  status?: number;
  code?: string;
  details?: unknown;
  isNetworkError: boolean;

  constructor(
    message: string,
    options?: {
      status?: number;
      code?: string;
      details?: unknown;
      isNetworkError?: boolean;
    }
  ) {
    super(message);
    this.name = "ApiError";
    this.status = options?.status;
    this.code = options?.code;
    this.details = options?.details;
    this.isNetworkError = options?.isNetworkError ?? false;
  }
}

const extractMessage = (data: unknown) => {
  if (!data || typeof data !== "object") {
    return "Request failed";
  }

  const candidate = data as Record<string, unknown>;
  const fromMessage = candidate.message;
  const fromError = candidate.error;

  if (typeof fromMessage === "string" && fromMessage.trim()) {
    return fromMessage;
  }

  if (typeof fromError === "string" && fromError.trim()) {
    return fromError;
  }

  return "Request failed";
};

export const normalizeApiError = (error: unknown): ApiError => {
  if (error instanceof ApiError) {
    return error;
  }

  if (axios.isAxiosError(error)) {
    const status = error.response?.status;
    const data = error.response?.data;
    const message = error.response
      ? extractMessage(data)
      : "Network error. Please check your connection.";

    return new ApiError(message, {
      status,
      code:
        data && typeof data === "object" && typeof (data as Record<string, unknown>).code === "string"
          ? ((data as Record<string, unknown>).code as string)
          : undefined,
      details: data,
      isNetworkError: !error.response,
    });
  }

  if (error instanceof Error) {
    return new ApiError(error.message);
  }

  return new ApiError("Unknown error occurred");
};

export const getAuthToken = () => {
  if (typeof window === "undefined") {
    return null;
  }
  return window.localStorage.getItem(AUTH_TOKEN_STORAGE_KEY);
};

export const setAuthToken = (token: string | null) => {
  if (typeof window === "undefined") {
    return;
  }

  if (token) {
    window.localStorage.setItem(AUTH_TOKEN_STORAGE_KEY, token);
    return;
  }

  window.localStorage.removeItem(AUTH_TOKEN_STORAGE_KEY);
};

export const clearAuthToken = () => setAuthToken(null);

export const apiClient = axios.create({
  baseURL: process.env.NEXT_PUBLIC_API_BASE_URL,
  withCredentials: true,
});

apiClient.interceptors.request.use((config) => {
  const token = getAuthToken();
  if (token) {
    config.headers = config.headers ?? {};
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

apiClient.interceptors.response.use(
  (response) => response,
  (error) => {
    const normalized = normalizeApiError(error);
    if (normalized.status === 401) {
      clearAuthToken();
    }
    return Promise.reject(normalized);
  }
);

export const parseWithSchema = <T>(
  schema: z.ZodType<T>,
  data: unknown,
  message = "Unexpected API response"
) => {
  const parsed = schema.safeParse(data);
  if (parsed.success) {
    return parsed.data;
  }

  throw new ApiError(message, {
    details: parsed.error.flatten(),
  });
};

export const isAuthError = (error: unknown) => {
  const normalized = normalizeApiError(error);
  return normalized.status === 401 || normalized.status === 403;
};

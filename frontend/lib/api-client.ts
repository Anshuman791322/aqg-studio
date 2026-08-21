import { env } from "@/lib/env";
import { createClient } from "@/lib/supabase/client";
import { ApiErrorResponse, ApiResponse, HealthStatus, VersionInfo } from "@/types/api";

export interface UserProfileData {
  user_id: string;
  email: string | null;
  role: string;
  display_name: string | null;
  app_metadata: Record<string, unknown>;
  user_metadata: Record<string, unknown>;
  quota: {
    today_requests: number;
    today_input_tokens: number;
    today_output_tokens: number;
    today_assessments: number;
  };
}

export class ApiClientError extends Error {
  public readonly code: string;
  public readonly statusCode: number;
  public readonly details: unknown[];
  public readonly requestId?: string | null;

  constructor(errorResponse: ApiErrorResponse, statusCode: number) {
    super(errorResponse.error.message);
    this.name = "ApiClientError";
    this.code = errorResponse.error.code;
    this.statusCode = statusCode;
    this.details = errorResponse.error.details || [];
    this.requestId = errorResponse.meta?.request_id;
  }
}

export interface RequestOptions extends RequestInit {
  token?: string;
  correlationId?: string;
}

/**
 * Type-safe HTTP client for AQG Studio backend API.
 */
export async function apiRequest<T>(
  endpoint: string,
  options: RequestOptions = {}
): Promise<ApiResponse<T>> {
  let { token } = options;
  const { correlationId, headers, ...customConfig } = options;

  // If no token is explicitly passed and running in browser, attempt to resolve from Supabase session
  if (!token && typeof window !== "undefined") {
    try {
      const supabase = createClient();
      const {
        data: { session },
      } = await supabase.auth.getSession();
      if (session?.access_token) {
        token = session.access_token;
      }
    } catch {
      // Graceful fallback if Supabase client cannot be initialized
    }
  }

  const requestCorrelationId =
    correlationId || `client_${Math.random().toString(36).substring(2, 11)}`;

  const requestHeaders = new Headers(headers);
  requestHeaders.set("Content-Type", "application/json");
  requestHeaders.set("X-Correlation-ID", requestCorrelationId);

  if (token) {
    requestHeaders.set("Authorization", `Bearer ${token}`);
  }

  const url = `${env.NEXT_PUBLIC_BACKEND_URL.replace(/\/$/, "")}${
    endpoint.startsWith("/") ? endpoint : `/${endpoint}`
  }`;

  const response = await fetch(url, {
    ...customConfig,
    headers: requestHeaders,
  });

  const responseData = await response.json();

  if (!response.ok || responseData.success === false) {
    throw new ApiClientError(responseData as ApiErrorResponse, response.status);
  }

  return responseData as ApiResponse<T>;
}

/**
 * Authenticated and System API helper functions.
 */
export const apiClient = {
  get: <T>(endpoint: string, options?: RequestOptions) =>
    apiRequest<T>(endpoint, { ...options, method: "GET" }),

  post: <T>(endpoint: string, body?: unknown, options?: RequestOptions) =>
    apiRequest<T>(endpoint, {
      ...options,
      method: "POST",
      body: body ? JSON.stringify(body) : undefined,
    }),

  async getAuthMe(token?: string): Promise<ApiResponse<UserProfileData>> {
    return apiRequest<UserProfileData>("/api/v1/auth/me", { token });
  },

  async getHealthLive(): Promise<HealthStatus> {
    const url = `${env.NEXT_PUBLIC_BACKEND_URL.replace(/\/$/, "")}/health/live`;
    const res = await fetch(url);
    return res.json();
  },

  async getHealthReady(): Promise<HealthStatus> {
    const url = `${env.NEXT_PUBLIC_BACKEND_URL.replace(/\/$/, "")}/health/ready`;
    const res = await fetch(url);
    return res.json();
  },

  async getVersion(): Promise<ApiResponse<VersionInfo>> {
    return apiRequest<VersionInfo>("/api/v1/version");
  },
};

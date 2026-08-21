/**
 * Standard API response and error types matching backend schemas.
 */

export interface ApiErrorDetail {
  field?: string | null;
  issue: string;
}

export interface ApiErrorPayload {
  code: string;
  message: string;
  details?: ApiErrorDetail[];
}

export interface ApiMetaPayload {
  timestamp: string;
  request_id?: string | null;
}

export interface ApiResponse<T> {
  success: boolean;
  data: T;
  meta: ApiMetaPayload;
}

export interface ApiErrorResponse {
  success: false;
  error: ApiErrorPayload;
  meta: ApiMetaPayload;
}

export interface HealthStatus {
  status: "ok" | "ready" | "error";
  database?: string;
  environment?: string;
}

export interface VersionInfo {
  name: string;
  version: string;
  api_version: string;
  environment: string;
  status: string;
}

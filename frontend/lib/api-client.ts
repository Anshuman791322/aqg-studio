import { env } from "@/lib/env";
import { createClient } from "@/lib/supabase/client";
import {
  ApiErrorResponse,
  ApiResponse,
  AssessmentBlueprintResponseData,
  AssessmentCreateRequest,
  AssessmentData,
  AssessmentReportData,
  DocumentAnalysisData,
  DocumentChunkData,
  DocumentData,
  DocumentInitiateRequest,
  DocumentInitiateResponse,
  EvaluationData,
  ExportCreateRequest,
  ExportData,
  HealthStatus,
  JobStatusData,
  QuestionData,
  QuestionUpdateRequest,
  VersionInfo,
} from "@/types/api";

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
 * Type-safe HTTP client for AQG Studio backend API with automatic Supabase JWT Bearer resolution.
 */
export async function apiRequest<T>(
  endpoint: string,
  options: RequestOptions = {}
): Promise<ApiResponse<T>> {
  let { token } = options;
  const { correlationId, headers, ...customConfig } = options;

  // Resolve active Supabase session token if not explicitly provided
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
  if (!requestHeaders.has("Content-Type") && !(customConfig.body instanceof FormData)) {
    requestHeaders.set("Content-Type", "application/json");
  }
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

  const responseData = await response.json().catch(() => ({
    success: false,
    error: {
      code: "NETWORK_ERROR",
      message: `Failed to parse response from server (${response.status} ${response.statusText})`,
    },
    meta: { timestamp: new Date().toISOString() },
  }));

  if (!response.ok || responseData.success === false) {
    throw new ApiClientError(responseData as ApiErrorResponse, response.status);
  }

  return responseData as ApiResponse<T>;
}

/**
 * Authenticated and System API helper functions for all AQG Studio modules.
 */
export const apiClient = {
  // Generic HTTP wrappers
  get: <T>(endpoint: string, options?: RequestOptions) =>
    apiRequest<T>(endpoint, { ...options, method: "GET" }),

  post: <T>(endpoint: string, body?: unknown, options?: RequestOptions) =>
    apiRequest<T>(endpoint, {
      ...options,
      method: "POST",
      body: body instanceof FormData ? body : body ? JSON.stringify(body) : undefined,
    }),

  patch: <T>(endpoint: string, body?: unknown, options?: RequestOptions) =>
    apiRequest<T>(endpoint, {
      ...options,
      method: "PATCH",
      body: body ? JSON.stringify(body) : undefined,
    }),

  delete: <T>(endpoint: string, options?: RequestOptions) =>
    apiRequest<T>(endpoint, { ...options, method: "DELETE" }),

  // ---------------------------------------------------------------------------
  // System & Auth
  // ---------------------------------------------------------------------------
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

  // ---------------------------------------------------------------------------
  // Document Ingestion & Management
  // ---------------------------------------------------------------------------
  async initiateDocumentUpload(
    data: DocumentInitiateRequest,
    token?: string
  ): Promise<ApiResponse<DocumentInitiateResponse>> {
    return apiRequest<DocumentInitiateResponse>("/api/v1/documents/initiate", {
      method: "POST",
      body: JSON.stringify(data),
      token,
    });
  },

  async completeDocumentUpload(
    documentId: string,
    token?: string
  ): Promise<ApiResponse<{ document_id: string; status: string }>> {
    return apiRequest<{ document_id: string; status: string }>(
      `/api/v1/documents/${documentId}/complete`,
      { method: "POST", token }
    );
  },

  async processDocument(
    documentId: string,
    file?: File,
    token?: string
  ): Promise<ApiResponse<JobStatusData>> {
    let body: BodyInit | undefined;
    if (file) {
      const formData = new FormData();
      formData.append("file", file);
      body = formData;
    }
    return apiRequest<JobStatusData>(`/api/v1/documents/${documentId}/process`, {
      method: "POST",
      body,
      token,
    });
  },

  async getDocumentStatus(
    documentId: string,
    token?: string
  ): Promise<ApiResponse<JobStatusData>> {
    return apiRequest<JobStatusData>(`/api/v1/documents/${documentId}/status`, { token });
  },

  async listDocuments(
    params?: { limit?: number; offset?: number },
    token?: string
  ): Promise<ApiResponse<DocumentData[]>> {
    const query = new URLSearchParams();
    if (params?.limit) query.set("limit", params.limit.toString());
    if (params?.offset) query.set("offset", params.offset.toString());
    const qs = query.toString() ? `?${query.toString()}` : "";
    return apiRequest<DocumentData[]>(`/api/v1/documents${qs}`, { token });
  },

  async getDocument(documentId: string, token?: string): Promise<ApiResponse<DocumentData>> {
    return apiRequest<DocumentData>(`/api/v1/documents/${documentId}`, { token });
  },

  async getDocumentChunks(
    documentId: string,
    token?: string
  ): Promise<ApiResponse<DocumentChunkData[]>> {
    return apiRequest<DocumentChunkData[]>(`/api/v1/documents/${documentId}/chunks`, { token });
  },

  async getDocumentAnalysis(
    documentId: string,
    token?: string
  ): Promise<ApiResponse<DocumentAnalysisData>> {
    return apiRequest<DocumentAnalysisData>(`/api/v1/documents/${documentId}/analysis`, {
      token,
    });
  },

  async deleteDocument(
    documentId: string,
    token?: string
  ): Promise<ApiResponse<{ deleted: boolean; document_id: string }>> {
    return apiRequest<{ deleted: boolean; document_id: string }>(
      `/api/v1/documents/${documentId}`,
      { method: "DELETE", token }
    );
  },

  // ---------------------------------------------------------------------------
  // Assessment Planning, Generation & Status
  // ---------------------------------------------------------------------------
  async createAssessment(
    data: AssessmentCreateRequest,
    token?: string
  ): Promise<ApiResponse<AssessmentBlueprintResponseData>> {
    return apiRequest<AssessmentBlueprintResponseData>("/api/v1/assessments", {
      method: "POST",
      body: JSON.stringify(data),
      token,
    });
  },

  async listAssessments(token?: string): Promise<ApiResponse<AssessmentData[]>> {
    return apiRequest<AssessmentData[]>("/api/v1/assessments", { token });
  },

  async getAssessment(
    assessmentId: string,
    token?: string
  ): Promise<ApiResponse<AssessmentData>> {
    return apiRequest<AssessmentData>(`/api/v1/assessments/${assessmentId}`, { token });
  },

  async getAssessmentBlueprint(
    assessmentId: string,
    token?: string
  ): Promise<ApiResponse<AssessmentBlueprintResponseData>> {
    return apiRequest<AssessmentBlueprintResponseData>(
      `/api/v1/assessments/${assessmentId}/blueprint`,
      { token }
    );
  },

  async generateAssessment(
    assessmentId: string,
    token?: string
  ): Promise<ApiResponse<JobStatusData>> {
    return apiRequest<JobStatusData>(`/api/v1/assessments/${assessmentId}/generate`, {
      method: "POST",
      token,
    });
  },

  async getAssessmentStatus(
    assessmentId: string,
    token?: string
  ): Promise<ApiResponse<JobStatusData>> {
    return apiRequest<JobStatusData>(`/api/v1/assessments/${assessmentId}/status`, { token });
  },

  async cancelAssessment(
    assessmentId: string,
    token?: string
  ): Promise<ApiResponse<JobStatusData>> {
    return apiRequest<JobStatusData>(`/api/v1/assessments/${assessmentId}/cancel`, {
      method: "POST",
      token,
    });
  },

  async deleteAssessment(
    assessmentId: string,
    token?: string
  ): Promise<ApiResponse<{ deleted: boolean; assessment_id: string }>> {
    return apiRequest<{ deleted: boolean; assessment_id: string }>(
      `/api/v1/assessments/${assessmentId}`,
      { method: "DELETE", token }
    );
  },

  async getAssessmentQuestions(
    assessmentId: string,
    token?: string
  ): Promise<ApiResponse<QuestionData[]>> {
    return apiRequest<QuestionData[]>(`/api/v1/assessments/${assessmentId}/questions`, {
      token,
    });
  },

  // ---------------------------------------------------------------------------
  // Question Review, Evaluation & Refinement
  // ---------------------------------------------------------------------------
  async getQuestion(questionId: string, token?: string): Promise<ApiResponse<QuestionData>> {
    return apiRequest<QuestionData>(`/api/v1/questions/${questionId}`, { token });
  },

  async updateQuestion(
    questionId: string,
    data: QuestionUpdateRequest,
    token?: string
  ): Promise<ApiResponse<QuestionData>> {
    return apiRequest<QuestionData>(`/api/v1/questions/${questionId}`, {
      method: "PATCH",
      body: JSON.stringify(data),
      token,
    });
  },

  async evaluateQuestion(
    questionId: string,
    token?: string
  ): Promise<ApiResponse<EvaluationData>> {
    return apiRequest<EvaluationData>(`/api/v1/questions/${questionId}/evaluate`, {
      method: "POST",
      token,
    });
  },

  async refineQuestion(
    questionId: string,
    customFeedback?: string,
    token?: string
  ): Promise<ApiResponse<QuestionData>> {
    return apiRequest<QuestionData>(`/api/v1/questions/${questionId}/refine`, {
      method: "POST",
      body: customFeedback ? JSON.stringify({ custom_feedback: customFeedback }) : undefined,
      token,
    });
  },

  async deleteQuestion(
    questionId: string,
    token?: string
  ): Promise<ApiResponse<{ deleted: boolean; question_id: string }>> {
    return apiRequest<{ deleted: boolean; question_id: string }>(
      `/api/v1/questions/${questionId}`,
      { method: "DELETE", token }
    );
  },

  async getQuestionEvaluations(
    questionId: string,
    token?: string
  ): Promise<ApiResponse<EvaluationData[]>> {
    return apiRequest<EvaluationData[]>(`/api/v1/questions/${questionId}/evaluations`, {
      token,
    });
  },

  // ---------------------------------------------------------------------------
  // Reporting & Export Center
  // ---------------------------------------------------------------------------
  async getAssessmentReport(
    assessmentId: string,
    token?: string
  ): Promise<ApiResponse<AssessmentReportData>> {
    return apiRequest<AssessmentReportData>(`/api/v1/assessments/${assessmentId}/report`, { token });
  },

  async listAssessmentExports(
    assessmentId: string,
    token?: string
  ): Promise<ApiResponse<ExportData[]>> {
    return apiRequest<ExportData[]>(`/api/v1/assessments/${assessmentId}/exports`, { token });
  },

  async createAssessmentExport(
    assessmentId: string,
    data: ExportCreateRequest,
    token?: string
  ): Promise<ApiResponse<ExportData>> {
    return apiRequest<ExportData>(`/api/v1/assessments/${assessmentId}/exports`, {
      method: "POST",
      body: JSON.stringify(data),
      token,
    });
  },

  async createExport(
    data: ExportCreateRequest,
    token?: string
  ): Promise<ApiResponse<ExportData>> {
    const assessmentId = data.assessment_id;
    if (assessmentId) {
      return this.createAssessmentExport(assessmentId, data, token);
    }
    return apiRequest<ExportData>("/api/v1/exports", {
      method: "POST",
      body: JSON.stringify(data),
      token,
    });
  },

  async getExportDownloadUrl(exportId: string): Promise<string> {
    return `${env.NEXT_PUBLIC_BACKEND_URL.replace(/\/$/, "")}/api/v1/exports/${exportId}/download`;
  },

  async deleteExport(
    exportId: string,
    token?: string
  ): Promise<ApiResponse<{ deleted: boolean; export_id: string }>> {
    return apiRequest<{ deleted: boolean; export_id: string }>(`/api/v1/exports/${exportId}`, {
      method: "DELETE",
      token,
    });
  },
};

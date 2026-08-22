import React from "react";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { ToastProvider } from "@/components/ui/ToastContext";
import DocumentDetailPage from "@/app/documents/[id]/page";
import * as apiClientModule from "@/lib/api-client";

jest.mock("next/navigation", () => ({
  useParams: () => ({ id: "doc-123" }),
  useRouter: () => ({
    push: jest.fn(),
  }),
}));

jest.mock("@/lib/api-client", () => {
  const actual = jest.requireActual("@/lib/api-client");
  const sampleDoc = {
    id: "doc-123",
    user_id: "user-123",
    original_filename: "Photosynthesis_Chapter.pdf",
    storage_path: "user-123/docs/doc-123.pdf",
    size_bytes: 4096000,
    declared_mime_type: "application/pdf",
    detected_mime_type: "application/pdf",
    checksum_sha256: "abcdef123456",
    status: "ready",
    error_message: null,
    page_count: 32,
    word_count: 12500,
    extracted_at: new Date().toISOString(),
    analyzed_at: new Date().toISOString(),
    created_at: new Date().toISOString(),
    updated_at: new Date().toISOString(),
  };

  const sampleChunks = [
    {
      id: "chunk-1",
      document_id: "doc-123",
      chunk_index: 0,
      content: "Photosynthesis is the process by which plants use sunlight...",
      token_count: 450,
      page_start: 1,
    },
  ];

  const sampleAnalysis = {
    document_id: "doc-123",
    topics: [
      {
        id: "top-1",
        name: "Light Reactions",
        importance_score: 1.0,
        concepts: [
          {
            id: "con-1",
            name: "Photosystem II",
            definition: "Absorbs light energy and oxidizes water.",
            difficulty_tier: "medium",
          },
        ],
      },
    ],
  };

  return {
    ...actual,
    apiClient: {
      ...actual.apiClient,
      getDocument: jest.fn().mockResolvedValue({
        success: true,
        data: sampleDoc,
      }),
      getDocumentChunks: jest.fn().mockResolvedValue({
        success: true,
        data: sampleChunks,
      }),
      getDocumentAnalysis: jest.fn().mockResolvedValue({
        success: true,
        data: sampleAnalysis,
      }),
      processDocument: jest.fn().mockResolvedValue({
        success: true,
        data: { job_id: "job-1", status: "queued" },
      }),
      deleteDocument: jest.fn().mockResolvedValue({
        success: true,
        data: { deleted: true, document_id: "doc-123" },
      }),
    },
  };
});

describe("Document Detail & Inspector", () => {
  let queryClient: QueryClient;

  beforeEach(() => {
    queryClient = new QueryClient({
      defaultOptions: { queries: { retry: false } },
    });
    jest.clearAllMocks();
  });

  it("renders document metadata, knowledge map, and chunk statistics", async () => {
    render(
      <QueryClientProvider client={queryClient}>
        <ToastProvider>
          <DocumentDetailPage />
        </ToastProvider>
      </QueryClientProvider>
    );

    expect(await screen.findByText(/Photosynthesis_Chapter.pdf/i)).toBeInTheDocument();
    expect(await screen.findByText(/Light Reactions/i)).toBeInTheDocument();
    expect(await screen.findByText(/Photosystem II/i)).toBeInTheDocument();
    expect(await screen.findByText(/Photosynthesis is the process by which plants use sunlight/i)).toBeInTheDocument();
  });

  it("triggers reprocess mutation when reprocess button clicked", async () => {
    render(
      <QueryClientProvider client={queryClient}>
        <ToastProvider>
          <DocumentDetailPage />
        </ToastProvider>
      </QueryClientProvider>
    );

    await screen.findByText(/Photosynthesis_Chapter.pdf/i);

    const reprocessBtn = screen.getByRole("button", { name: /Reprocess/i });
    fireEvent.click(reprocessBtn);

    await waitFor(() => {
      expect(apiClientModule.apiClient.processDocument).toHaveBeenCalledWith("doc-123");
    });
  });
});

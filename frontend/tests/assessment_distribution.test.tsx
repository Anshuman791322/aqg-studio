import React from "react";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { ToastProvider } from "@/components/ui/ToastContext";
import NewAssessmentPage from "@/app/assessments/new/page";
import * as apiClientModule from "@/lib/api-client";

jest.mock("next/navigation", () => ({
  useRouter: () => ({
    push: jest.fn(),
  }),
  useSearchParams: () => new URLSearchParams({ document_id: "doc-123" }),
}));

jest.mock("@/lib/api-client", () => {
  const actual = jest.requireActual("@/lib/api-client");
  return {
    ...actual,
    apiClient: {
      ...actual.apiClient,
      listDocuments: jest.fn().mockResolvedValue({
        success: true,
        data: [
          {
            id: "doc-123",
            original_filename: "Cell_Biology.pdf",
            status: "ready",
            page_count: 24,
            word_count: 8500,
            size_bytes: 2048000,
          },
        ],
      }),
      getDocumentAnalysis: jest.fn().mockResolvedValue({
        success: true,
        data: {
          document_id: "doc-123",
          topics: [
            { id: "top-1", name: "Mitochondrial Function", importance_score: 1.0, concepts: [] },
            { id: "top-2", name: "Glycolysis & Krebs Cycle", importance_score: 0.9, concepts: [] },
          ],
        },
      }),
      createAssessment: jest.fn().mockResolvedValue({
        success: true,
        data: { assessment_id: "assessment-456" },
      }),
      generateAssessment: jest.fn().mockResolvedValue({
        success: true,
        data: { job_id: "job-789", status: "queued", progress: 0 },
      }),
    },
  };
});

describe("Assessment Blueprint Distribution Form", () => {
  let queryClient: QueryClient;

  beforeEach(() => {
    queryClient = new QueryClient({
      defaultOptions: { queries: { retry: false } },
    });
    jest.clearAllMocks();
  });

  it("renders preselected document and distribution sliders totaling 100%", async () => {
    render(
      <QueryClientProvider client={queryClient}>
        <ToastProvider>
          <NewAssessmentPage />
        </ToastProvider>
      </QueryClientProvider>
    );

    expect(await screen.findByDisplayValue(/Cell_Biology - Assessment/i)).toBeInTheDocument();
    expect(screen.getAllByText(/Total: 100%/i).length).toBeGreaterThanOrEqual(1);
    expect(screen.getByText(/Mitochondrial Function/i)).toBeInTheDocument();
    expect(screen.getByText(/Glycolysis & Krebs Cycle/i)).toBeInTheDocument();
  });

  it("triggers create and generate assessment on submit", async () => {
    render(
      <QueryClientProvider client={queryClient}>
        <ToastProvider>
          <NewAssessmentPage />
        </ToastProvider>
      </QueryClientProvider>
    );

    await screen.findByDisplayValue(/Cell_Biology - Assessment/i);

    const submitBtn = screen.getByRole("button", { name: /Generate Assessment/i });
    fireEvent.click(submitBtn);

    await waitFor(() => {
      expect(apiClientModule.apiClient.createAssessment).toHaveBeenCalledWith(
        expect.objectContaining({
          document_id: "doc-123",
          total_questions: 10,
        })
      );
      expect(apiClientModule.apiClient.generateAssessment).toHaveBeenCalledWith("assessment-456");
    });
  });
});

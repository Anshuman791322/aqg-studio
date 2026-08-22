import React from "react";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { ToastProvider } from "@/components/ui/ToastContext";
import AssessmentProgressPage from "@/app/assessments/[id]/progress/page";
import * as apiClientModule from "@/lib/api-client";

jest.mock("next/navigation", () => ({
  useParams: () => ({ id: "assessment-123" }),
  useRouter: () => ({
    push: jest.fn(),
  }),
}));

jest.mock("@/lib/api-client", () => {
  const actual = jest.requireActual("@/lib/api-client");
  return {
    ...actual,
    apiClient: {
      ...actual.apiClient,
      getAssessment: jest.fn().mockResolvedValue({
        success: true,
        data: {
          id: "assessment-123",
          name: "Cellular Respiration Quiz",
          status: "running",
          progress: 45,
          configuration: { total_questions: 10 },
          metrics: { accepted_questions: 4 },
        },
      }),
      getAssessmentStatus: jest.fn().mockResolvedValue({
        success: true,
        data: {
          job_id: "job-123",
          status: "running",
          progress: 45,
          current_step: "evaluate_batches",
          accepted_questions: 4,
          target_questions: 10,
        },
      }),
      cancelAssessment: jest.fn().mockResolvedValue({
        success: true,
        data: { job_id: "job-123", status: "cancelled" },
      }),
    },
  };
});

describe("Assessment Progress Polling & Resumability", () => {
  let queryClient: QueryClient;

  beforeEach(() => {
    queryClient = new QueryClient({
      defaultOptions: { queries: { retry: false } },
    });
    jest.clearAllMocks();
  });

  it("displays current pipeline stage, progress percentage, and question counters", async () => {
    render(
      <QueryClientProvider client={queryClient}>
        <ToastProvider>
          <AssessmentProgressPage />
        </ToastProvider>
      </QueryClientProvider>
    );

    expect(await screen.findByText(/Cellular Respiration Quiz/i)).toBeInTheDocument();
    expect(screen.getByText(/evaluate_batches/i)).toBeInTheDocument();
    expect(screen.getByText(/45%/i)).toBeInTheDocument();
    expect(screen.getByText(/4 \/ 10/i)).toBeInTheDocument();
    expect(screen.getByText(/3\. 10-Metric Quality Evaluation/i)).toBeInTheDocument();
  });

  it("allows user to trigger cancellation dialog and abort job", async () => {
    render(
      <QueryClientProvider client={queryClient}>
        <ToastProvider>
          <AssessmentProgressPage />
        </ToastProvider>
      </QueryClientProvider>
    );

    const cancelBtn = await screen.findByRole("button", { name: /Cancel/i });
    fireEvent.click(cancelBtn);

    const confirmModalBtn = screen.getByRole("button", { name: /Cancel Job/i });
    fireEvent.click(confirmModalBtn);

    await waitFor(() => {
      expect(apiClientModule.apiClient.cancelAssessment).toHaveBeenCalledWith("assessment-123");
    });
  });
});

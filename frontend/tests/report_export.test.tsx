import React from "react";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { ToastProvider } from "@/components/ui/ToastContext";
import AssessmentReportPage from "@/app/assessments/[id]/report/page";
import * as apiClientModule from "@/lib/api-client";

jest.mock("next/navigation", () => ({
  useParams: () => ({ id: "assessment-123" }),
  useRouter: () => ({
    push: jest.fn(),
  }),
}));

jest.mock("@/lib/api-client", () => {
  const actual = jest.requireActual("@/lib/api-client");
  const sampleAssessment = {
    id: "assessment-123",
    name: "Cell Biology Midterm",
    status: "ready",
    progress: 100,
    configuration: { total_questions: 10 },
    metrics: {
      average_quality_score: 0.94,
      accepted_questions: 8,
      refinement_count: 2,
      regeneration_count: 1,
    },
  };

  const sampleQuestions = [
    {
      id: "q-1",
      assessment_id: "assessment-123",
      question_type: "mcq_single",
      question_text: "What is the powerhouse of the cell?",
      correct_answer: "A",
      explanation: "Mitochondria produce ATP.",
      difficulty: "easy",
      bloom_level: "remember",
      quality_score: 0.95,
      status: "approved",
      version: 1,
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString(),
    },
    {
      id: "q-2",
      assessment_id: "assessment-123",
      question_type: "short_answer",
      question_text: "Explain the chemiosmotic hypothesis.",
      correct_answer: "Proton gradient drives ATP synthesis.",
      explanation: "Peter Mitchell model.",
      difficulty: "hard",
      bloom_level: "analyze",
      quality_score: 0.92,
      status: "approved",
      version: 1,
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString(),
    },
  ];

  return {
    ...actual,
    apiClient: {
      ...actual.apiClient,
      getAssessmentReport: jest.fn().mockResolvedValue({
        success: true,
        data: {
          assessment_id: "assessment-123",
          document_id: "doc-123",
          assessment_name: "Cell Biology Midterm",
          document_filename: "Cell_Biology_Chapter.pdf",
          status: "ready",
          metrics: {
            total_requested: 10,
            total_generated: 10,
            total_accepted: 8,
            total_rejected: 2,
            total_flagged: 0,
            total_draft: 0,
            approval_rate: 80.0,
            average_overall_quality: 0.94,
            average_groundedness: 0.98,
            average_correctness: 0.99,
            average_clarity: 0.95,
            average_distractor_quality: 0.92,
            number_refined: 2,
            number_regenerated: 1,
            duplicate_count: 0,
            failed_blueprints: 0,
          },
          question_type_distribution: {
            mcq_single: { count: 8, percentage: 80.0 },
            short_answer: { count: 2, percentage: 20.0 },
          },
          difficulty_distribution: {
            easy: { count: 4, percentage: 40.0 },
            medium: { count: 4, percentage: 40.0 },
            hard: { count: 2, percentage: 20.0 },
          },
          bloom_distribution: {
            remember: { count: 4, percentage: 40.0 },
            understand: { count: 4, percentage: 40.0 },
            apply: { count: 2, percentage: 20.0 },
            analyze: { count: 0, percentage: 0.0 },
            evaluate: { count: 0, percentage: 0.0 },
            create: { count: 0, percentage: 0.0 },
          },
          topic_coverage: [
            { topic_name: "Cell Membrane", question_count: 5, is_covered: true, importance_score: 1.0 },
            { topic_name: "Cell Organelles", question_count: 5, is_covered: true, importance_score: 1.0 },
          ],
          available_exports: [],
        },
      }),
      getAssessment: jest.fn().mockResolvedValue({
        success: true,
        data: sampleAssessment,
      }),
      getAssessmentQuestions: jest.fn().mockResolvedValue({
        success: true,
        data: sampleQuestions,
      }),
      getExportDownloadUrl: jest.fn().mockResolvedValue("https://example.com/download/exam.pdf"),
      createExport: jest.fn().mockResolvedValue({
        success: true,
        data: {
          id: "export-1",
          assessment_id: "assessment-123",
          format: "pdf",
          download_url: "https://example.com/download/exam.pdf",
          status: "ready",
        },
      }),
    },
  };
});

describe("Assessment Report & Export Center", () => {
  let queryClient: QueryClient;

  beforeEach(() => {
    queryClient = new QueryClient({
      defaultOptions: { queries: { retry: false } },
    });
    jest.clearAllMocks();
  });

  it("calculates and displays quality metrics and distribution totals", async () => {
    render(
      <QueryClientProvider client={queryClient}>
        <ToastProvider>
          <AssessmentReportPage />
        </ToastProvider>
      </QueryClientProvider>
    );

    expect(await screen.findByText(/Cell Biology Midterm/i)).toBeInTheDocument();
    expect(screen.getByText(/Item Format Distribution/i)).toBeInTheDocument();
    expect(screen.getByText(/Difficulty Tier Breakdown/i)).toBeInTheDocument();
    expect(screen.getByText(/LMS & Document Export Center/i)).toBeInTheDocument();
  });

  it("triggers export mutation with selected format and options", async () => {
    render(
      <QueryClientProvider client={queryClient}>
        <ToastProvider>
          <AssessmentReportPage />
        </ToastProvider>
      </QueryClientProvider>
    );

    await screen.findByText(/Cell Biology Midterm/i);

    const exportBtn = screen.getByRole("button", { name: /Download PDF Package/i });
    fireEvent.click(exportBtn);

    await waitFor(() => {
      expect(apiClientModule.apiClient.createExport).toHaveBeenCalledWith(
        expect.objectContaining({
          assessment_id: "assessment-123",
          format: "pdf",
          configuration: expect.objectContaining({
            include_answers: true,
            include_explanations: true,
          }),
        })
      );
    });
  });
});

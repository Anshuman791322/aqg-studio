import React from "react";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { ToastProvider } from "@/components/ui/ToastContext";
import QuestionReviewPage from "@/app/assessments/[id]/review/page";
import * as apiClientModule from "@/lib/api-client";

jest.mock("next/navigation", () => ({
  useParams: () => ({ id: "assessment-123" }),
  useRouter: () => ({
    push: jest.fn(),
  }),
}));

jest.mock("@/lib/api-client", () => {
  const actual = jest.requireActual("@/lib/api-client");
  const sampleQuestions = [
    {
      id: "q-1",
      assessment_id: "assessment-123",
      question_type: "mcq_single",
      question_text: "What is the primary role of ATP synthase in mitochondria?",
      options: [
        { key: "A", text: "Synthesizes ATP using proton motive force", is_correct: true },
        { key: "B", text: "Pumps electrons into the cytoplasm", is_correct: false },
        { key: "C", text: "Hydrolyzes glucose directly", is_correct: false },
        { key: "D", text: "Oxidizes NADH in the nucleus", is_correct: false },
      ],
      correct_answer: "A",
      explanation: "ATP synthase utilizes the electrochemical proton gradient across the inner membrane.",
      difficulty: "medium",
      bloom_level: "understand",
      quality_score: 0.96,
      status: "approved",
      metadata: {
        topic: "Mitochondrial Respiration",
        supporting_evidence: {
          direct_quote: "ATP synthase generates ATP using the proton gradient.",
          page_number: 24,
        },
      },
      version: 1,
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString(),
      evaluations: [
        {
          id: "eval-1",
          question_id: "q-1",
          user_id: "user-1",
          correctness_score: 1.0,
          grounding_score: 0.98,
          clarity_score: 0.95,
          overall_quality_score: 0.96,
          decision: "ACCEPT",
          created_at: new Date().toISOString(),
        },
      ],
    },
    {
      id: "q-2",
      assessment_id: "assessment-123",
      question_type: "true_false",
      question_text: "Glycolysis requires molecular oxygen to produce pyruvate.",
      correct_answer: "False",
      explanation: "Glycolysis is an anaerobic pathway that operates in the absence of oxygen.",
      difficulty: "easy",
      bloom_level: "remember",
      quality_score: 0.92,
      status: "draft",
      metadata: {
        topic: "Glycolysis",
      },
      version: 1,
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString(),
    },
  ];

  return {
    ...actual,
    apiClient: {
      ...actual.apiClient,
      getAssessment: jest.fn().mockResolvedValue({
        success: true,
        data: {
          id: "assessment-123",
          name: "Cell Bio Exam",
          status: "ready",
          progress: 100,
        },
      }),
      getAssessmentQuestions: jest.fn().mockResolvedValue({
        success: true,
        data: sampleQuestions,
      }),
      updateQuestion: jest.fn().mockResolvedValue({
        success: true,
        data: { ...sampleQuestions[0], status: "approved" },
      }),
      refineQuestion: jest.fn().mockResolvedValue({
        success: true,
        data: { ...sampleQuestions[1], status: "draft" },
      }),
      deleteQuestion: jest.fn().mockResolvedValue({
        success: true,
        data: { deleted: true, question_id: "q-1" },
      }),
    },
  };
});

describe("Question Review Studio", () => {
  let queryClient: QueryClient;

  beforeEach(() => {
    queryClient = new QueryClient({
      defaultOptions: { queries: { retry: false } },
    });
    jest.clearAllMocks();
  });

  it("renders generated questions with options, citations, and quality scores", async () => {
    render(
      <QueryClientProvider client={queryClient}>
        <ToastProvider>
          <QuestionReviewPage />
        </ToastProvider>
      </QueryClientProvider>
    );

    expect(await screen.findByText(/What is the primary role of ATP synthase in mitochondria\?/i)).toBeInTheDocument();
    expect(screen.getByText(/Synthesizes ATP using proton motive force/i)).toBeInTheDocument();
    expect(screen.getByText(/Page 24/i)).toBeInTheDocument();
    expect(screen.getByText(/Score: 96%/i)).toBeInTheDocument();
    expect(screen.getByText(/Glycolysis requires molecular oxygen/i)).toBeInTheDocument();
  });

  it("allows inline question stem editing", async () => {
    render(
      <QueryClientProvider client={queryClient}>
        <ToastProvider>
          <QuestionReviewPage />
        </ToastProvider>
      </QueryClientProvider>
    );

    await screen.findByText(/What is the primary role of ATP synthase in mitochondria\?/i);

    const editBtns = screen.getAllByRole("button", { name: /Edit/i });
    fireEvent.click(editBtns[0]);

    const stemInput = screen.getByDisplayValue(/What is the primary role of ATP synthase in mitochondria\?/i);
    fireEvent.change(stemInput, { target: { value: "Modified ATP synthase question stem" } });

    const saveBtn = screen.getByRole("button", { name: /Save Edits/i });
    fireEvent.click(saveBtn);

    await waitFor(() => {
      expect(apiClientModule.apiClient.updateQuestion).toHaveBeenCalledWith(
        "q-1",
        expect.objectContaining({
          question_text: "Modified ATP synthase question stem",
        })
      );
    });
  });

  it("allows approving a question", async () => {
    render(
      <QueryClientProvider client={queryClient}>
        <ToastProvider>
          <QuestionReviewPage />
        </ToastProvider>
      </QueryClientProvider>
    );

    await screen.findByText(/What is the primary role of ATP synthase in mitochondria\?/i);

    const approveBtns = screen.getAllByRole("button", { name: /Approve/i });
    fireEvent.click(approveBtns[0]);

    await waitFor(() => {
      expect(apiClientModule.apiClient.updateQuestion).toHaveBeenCalledWith(
        "q-1",
        expect.objectContaining({
          status: "approved",
        })
      );
    });
  });

  it("handles rejection and delete confirmation dialog flows", async () => {
    render(
      <QueryClientProvider client={queryClient}>
        <ToastProvider>
          <QuestionReviewPage />
        </ToastProvider>
      </QueryClientProvider>
    );

    await screen.findByText(/What is the primary role of ATP synthase in mitochondria\?/i);

    const rejectBtns = screen.getAllByRole("button", { name: /Reject/i });
    fireEvent.click(rejectBtns[0]);

    await waitFor(() => {
      expect(apiClientModule.apiClient.updateQuestion).toHaveBeenCalledWith(
        "q-1",
        expect.objectContaining({
          status: "rejected",
        })
      );
    });

    const deleteBtns = screen.getAllByRole("button", { name: /Delete Question/i });
    fireEvent.click(deleteBtns[0]);

    const confirmDeleteBtn = screen.getByRole("button", { name: /Delete Item/i });
    fireEvent.click(confirmDeleteBtn);

    await waitFor(() => {
      expect(apiClientModule.apiClient.deleteQuestion).toHaveBeenCalledWith("q-1");
    });
  });
});

import React from "react";
import { render, screen } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { ToastProvider } from "@/components/ui/ToastContext";
import DashboardPage from "@/app/dashboard/page";

// Mock Next Navigation
jest.mock("next/navigation", () => ({
  useRouter: () => ({
    push: jest.fn(),
    replace: jest.fn(),
    prefetch: jest.fn(),
  }),
  useParams: () => ({}),
  useSearchParams: () => new URLSearchParams(),
}));

// Mock API Client
jest.mock("@/lib/api-client", () => {
  const actual = jest.requireActual("@/lib/api-client");
  return {
    ...actual,
    apiClient: {
      ...actual.apiClient,
      getAuthMe: jest.fn().mockResolvedValue({
        success: true,
        data: {
          user_id: "user-123",
          email: "educator@example.com",
          role: "authenticated",
          display_name: "Dr. Educator",
          quota: {
            today_requests: 12,
            today_input_tokens: 4500,
            today_output_tokens: 1200,
            today_assessments: 2,
          },
        },
      }),
      listDocuments: jest.fn().mockResolvedValue({
        success: true,
        data: [],
      }),
      listAssessments: jest.fn().mockResolvedValue({
        success: true,
        data: [],
      }),
    },
  };
});

describe("Dashboard & Auth Guard", () => {
  let queryClient: QueryClient;

  beforeEach(() => {
    queryClient = new QueryClient({
      defaultOptions: {
        queries: { retry: false },
      },
    });
    jest.clearAllMocks();
  });

  it("renders authenticated user profile and quota metrics", async () => {
    render(
      <QueryClientProvider client={queryClient}>
        <ToastProvider>
          <DashboardPage />
        </ToastProvider>
      </QueryClientProvider>
    );

    expect(await screen.findByText(/Welcome back, Dr. Educator/i)).toBeInTheDocument();
    expect(screen.getByText(/12 \/ 500/i)).toBeInTheDocument();
    expect(screen.getByText(/No documents uploaded yet/i)).toBeInTheDocument();
    expect(screen.getByText(/No assessments generated yet/i)).toBeInTheDocument();
  });
});

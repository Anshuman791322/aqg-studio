"use client";

import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { useState } from "react";

export function QueryProvider({ children }: { children: React.ReactNode }) {
  const [queryClient] = useState(
    () =>
      new QueryClient({
        defaultOptions: {
          queries: {
            staleTime: 5 * 1000, // 5 seconds
            refetchOnWindowFocus: false,
            retry: (failureCount, error) => {
              // Do not retry 4xx errors
              const is4xx =
                typeof error === "object" &&
                error !== null &&
                "statusCode" in error &&
                typeof (error as { statusCode: number }).statusCode === "number" &&
                (error as { statusCode: number }).statusCode >= 400 &&
                (error as { statusCode: number }).statusCode < 500;
              if (is4xx) return false;
              return failureCount < 2;
            },
          },
        },
      })
  );

  return <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>;
}

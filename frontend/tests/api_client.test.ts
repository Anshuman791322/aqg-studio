import { ApiClientError, apiRequest } from "@/lib/api-client";

describe("API Client & Auth Header Attachment", () => {
  beforeEach(() => {
    // Mock global fetch
    global.fetch = jest.fn();
  });

  afterEach(() => {
    jest.restoreAllMocks();
  });

  it("attaches Authorization Bearer token and X-Correlation-ID headers", async () => {
    const mockResponse = {
      success: true,
      data: { name: "AQG Studio Backend", version: "0.1.0" },
      meta: { timestamp: new Date().toISOString(), request_id: "req-123" },
    };

    (global.fetch as jest.Mock).mockResolvedValueOnce({
      ok: true,
      status: 200,
      json: async () => mockResponse,
    });

    const res = await apiRequest("/api/v1/version", {
      token: "test-jwt-token-12345",
    });

    expect(res.success).toBe(true);
    expect(res.data).toEqual(mockResponse.data);

    expect(global.fetch).toHaveBeenCalledWith(
      expect.stringContaining("/api/v1/version"),
      expect.objectContaining({
        headers: expect.any(Headers),
      })
    );

    const callHeaders = (global.fetch as jest.Mock).mock.calls[0][1].headers as Headers;
    expect(callHeaders.get("Authorization")).toBe("Bearer test-jwt-token-12345");
    expect(callHeaders.get("X-Correlation-ID")).toBeDefined();
  });

  it("throws normalized ApiClientError on 4xx/5xx responses", async () => {
    const errorPayload = {
      success: false,
      error: {
        code: "UNAUTHORIZED",
        message: "Invalid or expired JWT bearer token",
      },
      meta: { timestamp: new Date().toISOString(), request_id: "err-401" },
    };

    (global.fetch as jest.Mock).mockResolvedValueOnce({
      ok: false,
      status: 401,
      json: async () => errorPayload,
    });

    await expect(
      apiRequest("/api/v1/documents", { token: "bad-token" })
    ).rejects.toThrow(ApiClientError);
  });
});

import { beforeEach, describe, expect, it, vi } from "vitest";

import { ApiError } from "./httpClient";
import { getMe, login, logout } from "./auth";

const fetchMock = vi.fn();
vi.stubGlobal("fetch", fetchMock);

describe("auth API client", () => {
  beforeEach(() => {
    fetchMock.mockReset();
  });

  it("sends login payload to /api/v1/auth/login", async () => {
    fetchMock.mockResolvedValue(
      new Response(
        JSON.stringify({
          access_token: "access-token",
          refresh_token: "refresh-token",
          token_type: "bearer",
          expires_in: 3600,
          session_id: "11111111-1111-1111-1111-111111111111",
        }),
        {
          status: 200,
          headers: { "Content-Type": "application/json" },
        },
      ),
    );

    const response = await login({ identifier: "staff", password: "secret" });

    expect(response.access_token).toBe("access-token");
    const [input, init] = fetchMock.mock.calls[0] as [RequestInfo | URL, RequestInit];
    expect(String(input)).toContain("/api/v1/auth/login");
    expect(init.method).toBe("POST");
    expect(init.headers).toMatchObject({ "Content-Type": "application/json" });
    expect(init.body).toBe(JSON.stringify({ identifier: "staff", password: "secret" }));
  });

  it("sends Authorization bearer token on getMe", async () => {
    fetchMock.mockResolvedValue(
      new Response(
        JSON.stringify({
          subject_id: "11111111-1111-1111-1111-111111111111",
          role: "hr",
          session_id: "22222222-2222-2222-2222-222222222222",
          access_token_expires_at: 1893456000,
        }),
        {
          status: 200,
          headers: { "Content-Type": "application/json" },
        },
      ),
    );

    await getMe("access-token");

    const [input, init] = fetchMock.mock.calls[0] as [RequestInfo | URL, RequestInit];
    expect(String(input)).toContain("/api/v1/auth/me");
    expect(init.method).toBe("GET");
    expect(init.headers).toMatchObject({ Authorization: "Bearer access-token" });
  });

  it("sends POST /api/v1/auth/logout with Authorization bearer header", async () => {
    fetchMock.mockResolvedValue(new Response("", { status: 200 }));

    await logout("access-token");

    const [input, init] = fetchMock.mock.calls[0] as [RequestInfo | URL, RequestInit];
    expect(String(input)).toContain("/api/v1/auth/logout");
    expect(init.method).toBe("POST");
    expect(init.headers).toMatchObject({ Authorization: "Bearer access-token" });
    expect(init.body).toBeUndefined();
  });

  it("throws ApiError with status/detail on login failure", async () => {
    fetchMock.mockResolvedValue(
      new Response(JSON.stringify({ detail: "invalid_credentials" }), {
        status: 401,
        headers: { "Content-Type": "application/json" },
      }),
    );

    let capturedError: unknown;
    try {
      await login({ identifier: "staff", password: "wrong-secret" });
    } catch (error) {
      capturedError = error;
    }

    expect(capturedError).toBeInstanceOf(ApiError);
    expect(capturedError).toMatchObject({
      status: 401,
      detail: "invalid_credentials",
    });
  });
});

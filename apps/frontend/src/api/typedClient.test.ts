import { beforeEach, describe, expect, it, vi } from "vitest";

const fetchMock = vi.fn();
vi.stubGlobal("fetch", fetchMock);

describe("typedApiClient", () => {
  beforeEach(() => {
    fetchMock.mockReset();
    vi.resetModules();
    vi.unstubAllEnvs();
  });

  it("prefixes requests with VITE_API_BASE_URL and trims trailing slash", async () => {
    vi.stubEnv("VITE_API_BASE_URL", "http://localhost:8000/");
    fetchMock.mockResolvedValue(
      new Response(JSON.stringify({ ok: true }), {
        status: 200,
        headers: { "Content-Type": "application/json" },
      }),
    );

    const { typedApiClient } = await import("./typedClient");

    await typedApiClient.get<{ ok: boolean }>("/api/v1/auth/me");

    const [input] = fetchMock.mock.calls[0] as [RequestInfo | URL, RequestInit];
    expect(String(input)).toBe("http://localhost:8000/api/v1/auth/me");
  });

  it("falls back to relative URLs when VITE_API_BASE_URL is blank", async () => {
    vi.stubEnv("VITE_API_BASE_URL", "   ");
    fetchMock.mockResolvedValue(
      new Response(JSON.stringify({ ok: true }), {
        status: 200,
        headers: { "Content-Type": "application/json" },
      }),
    );

    const { typedApiClient } = await import("./typedClient");

    await typedApiClient.get<{ ok: boolean }>("/api/v1/auth/me");

    const [input] = fetchMock.mock.calls[0] as [RequestInfo | URL, RequestInit];
    expect(String(input)).toBe("/api/v1/auth/me");
  });

  it("sends FormData payloads without forcing JSON headers", async () => {
    vi.stubEnv("VITE_API_BASE_URL", "http://localhost:8000");
    fetchMock.mockResolvedValue(
      new Response(JSON.stringify({ ok: true }), {
        status: 200,
        headers: { "Content-Type": "application/json" },
      }),
    );

    const { typedApiClient } = await import("./typedClient");
    const formData = new FormData();
    formData.set("file", new Blob(["file-content"], { type: "text/plain" }), "note.txt");

    await typedApiClient.postForm<{ ok: boolean }>("/api/v1/upload", formData);

    const [input, init] = fetchMock.mock.calls[0] as [RequestInfo | URL, RequestInit];
    expect(String(input)).toBe("http://localhost:8000/api/v1/upload");
    expect(init.method).toBe("POST");
    expect(init.body).toBe(formData);
    expect(init.headers).toBeUndefined();
  });

  it("sends JSON PUT payloads with content-type header", async () => {
    vi.stubEnv("VITE_API_BASE_URL", "http://localhost:8000");
    fetchMock.mockResolvedValue(
      new Response(JSON.stringify({ ok: true }), {
        status: 200,
        headers: { "Content-Type": "application/json" },
      }),
    );

    const { typedApiClient } = await import("./typedClient");

    await typedApiClient.put<{ ok: boolean }>("/api/v1/items/123", { status: "saved" });

    const [input, init] = fetchMock.mock.calls[0] as [RequestInfo | URL, RequestInit];
    expect(String(input)).toBe("http://localhost:8000/api/v1/items/123");
    expect(init.method).toBe("PUT");
    expect(init.headers).toEqual({ "Content-Type": "application/json" });
    expect(init.body).toBe(JSON.stringify({ status: "saved" }));
  });
});

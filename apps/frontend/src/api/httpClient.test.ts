import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { ApiError, apiRequest, downloadFile } from "./httpClient";

const fetchMock = vi.fn();
vi.stubGlobal("fetch", fetchMock);

const {
  captureExceptionMock,
  scopeSetExtraMock,
  scopeSetTagMock,
  withScopeMock,
} = vi.hoisted(() => ({
  captureExceptionMock: vi.fn(),
  scopeSetExtraMock: vi.fn(),
  scopeSetTagMock: vi.fn(),
  withScopeMock: vi.fn(),
}));

vi.mock("@sentry/react", () => ({
  captureException: captureExceptionMock,
  setTag: vi.fn(),
  withScope: withScopeMock,
}));

describe("apiRequest observability", () => {
  let clickSpy: ReturnType<typeof vi.spyOn>;

  beforeEach(() => {
    fetchMock.mockReset();
    captureExceptionMock.mockReset();
    scopeSetExtraMock.mockReset();
    scopeSetTagMock.mockReset();
    withScopeMock.mockReset();
    withScopeMock.mockImplementation((callback: (scope: unknown) => void) => {
      callback({
        setExtra: scopeSetExtraMock,
        setTag: scopeSetTagMock,
      });
    });
    window.localStorage.clear();
    window.history.pushState({}, "", "/");
    window.URL.createObjectURL = vi.fn(() => "blob:download");
    window.URL.revokeObjectURL = vi.fn();
    clickSpy = vi.spyOn(HTMLAnchorElement.prototype, "click").mockImplementation(() => {});
  });

  afterEach(() => {
    clickSpy.mockRestore();
  });

  it("captures API error responses with route and HTTP metadata", async () => {
    window.history.pushState({}, "", "/candidate");
    fetchMock.mockResolvedValue(
      new Response(JSON.stringify({ detail: "http_409" }), {
        status: 409,
        headers: { "Content-Type": "application/json" },
      }),
    );

    await expect(apiRequest("/api/v1/public/cv-parsing-jobs/job-id")).rejects.toBeInstanceOf(
      ApiError,
    );

    expect(withScopeMock).toHaveBeenCalledTimes(1);
    expect(scopeSetTagMock).toHaveBeenCalledWith("workspace", "candidate");
    expect(scopeSetTagMock).toHaveBeenCalledWith("role", "anonymous");
    expect(scopeSetTagMock).toHaveBeenCalledWith("route", "/candidate");
    expect(scopeSetTagMock).toHaveBeenCalledWith("http_method", "GET");
    expect(scopeSetTagMock).toHaveBeenCalledWith("http_status", "409");
    expect(scopeSetExtraMock).toHaveBeenCalledWith(
      "http_request_path",
      "/api/v1/public/cv-parsing-jobs/job-id",
    );
    expect(scopeSetExtraMock).toHaveBeenCalledWith("http_detail", "http_409");
    expect(captureExceptionMock).toHaveBeenCalledTimes(1);
  });

  it("captures network failures with the active workspace tags", async () => {
    window.localStorage.setItem("hrm_access_token", "token");
    window.localStorage.setItem("hrm_user_role", "hr");
    window.history.pushState({}, "", "/hr");
    const networkError = new Error("network down");
    fetchMock.mockRejectedValue(networkError);

    await expect(apiRequest("/api/v1/vacancies")).rejects.toThrow("network down");

    expect(withScopeMock).toHaveBeenCalledTimes(1);
    expect(scopeSetTagMock).toHaveBeenCalledWith("workspace", "hr");
    expect(scopeSetTagMock).toHaveBeenCalledWith("role", "hr");
    expect(scopeSetTagMock).toHaveBeenCalledWith("route", "/hr");
    expect(scopeSetTagMock).toHaveBeenCalledWith("http_method", "GET");
    expect(scopeSetExtraMock).toHaveBeenCalledWith("http_request_path", "/api/v1/vacancies");
    expect(captureExceptionMock).toHaveBeenCalledWith(networkError);
  });

  it("captures binary download failures with route and HTTP metadata", async () => {
    window.localStorage.setItem("hrm_access_token", "token");
    window.localStorage.setItem("hrm_user_role", "accountant");
    window.history.pushState({}, "", "/accountant");
    fetchMock.mockResolvedValue(
      new Response(JSON.stringify({ detail: "http_403" }), {
        status: 403,
        headers: { "Content-Type": "application/json" },
      }),
    );

    await expect(downloadFile("/api/v1/accounting/workspace/export?format=csv")).rejects.toBeInstanceOf(
      ApiError,
    );

    expect(withScopeMock).toHaveBeenCalledTimes(1);
    expect(scopeSetTagMock).toHaveBeenCalledWith("workspace", "accountant");
    expect(scopeSetTagMock).toHaveBeenCalledWith("role", "accountant");
    expect(scopeSetTagMock).toHaveBeenCalledWith("route", "/accountant");
    expect(scopeSetTagMock).toHaveBeenCalledWith("http_method", "GET");
    expect(scopeSetTagMock).toHaveBeenCalledWith("http_status", "403");
    expect(scopeSetExtraMock).toHaveBeenCalledWith(
      "http_request_path",
      "/api/v1/accounting/workspace/export?format=csv",
    );
    expect(scopeSetExtraMock).toHaveBeenCalledWith("http_detail", "http_403");
  });
});

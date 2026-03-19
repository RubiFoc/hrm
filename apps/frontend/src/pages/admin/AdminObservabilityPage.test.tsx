import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { MemoryRouter } from "react-router-dom";
import i18n from "i18next";

import "../../app/i18n";
import { AdminObservabilityPage } from "./AdminObservabilityPage";

const fetchMock = vi.fn();
vi.stubGlobal("fetch", fetchMock);

const { captureExceptionMock, scopeSetExtraMock, scopeSetTagMock, withScopeMock } = vi.hoisted(
  () => ({
    captureExceptionMock: vi.fn(),
    scopeSetExtraMock: vi.fn(),
    scopeSetTagMock: vi.fn(),
    withScopeMock: vi.fn(),
  }),
);

vi.mock("@sentry/react", () => ({
  captureException: captureExceptionMock,
  setTag: vi.fn(),
  withScope: withScopeMock,
}));

function renderPage() {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: { retry: false },
      mutations: { retry: false },
    },
  });

  render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter>
        <AdminObservabilityPage />
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

function jsonResponse(body: unknown, status = 200): Promise<Response> {
  return Promise.resolve(
    new Response(JSON.stringify(body), {
      status,
      headers: { "Content-Type": "application/json" },
    }),
  );
}

describe("AdminObservabilityPage", () => {
  beforeEach(async () => {
    window.localStorage.clear();
    window.localStorage.setItem("hrm_access_token", "admin-token");
    window.localStorage.setItem("hrm_user_role", "admin");
    window.history.pushState({}, "", "/admin/observability");
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
    await i18n.changeLanguage("ru");
  });

  afterEach(() => {
    cleanup();
  });

  it("renders backend health and audit preview in RU and EN", async () => {
    fetchMock.mockImplementation((input: RequestInfo | URL) => {
      const url = String(input);
      if (url.endsWith("/health")) {
        return jsonResponse({ status: "ok" });
      }
      if (url.includes("/api/v1/audit/events?")) {
        return jsonResponse({
          items: [
            {
              event_id: "11111111-1111-4111-8111-111111111111",
              occurred_at: "2026-03-19T10:00:00Z",
              source: "api",
              actor_sub: "admin-1",
              actor_role: "admin",
              action: "vacancy:create",
              resource_type: "vacancy",
              resource_id: "vacancy-1",
              result: "success",
              reason: "created",
              correlation_id: "corr-1",
              ip: "127.0.0.1",
              user_agent: "Mozilla/5.0",
            },
          ],
          total: 1,
          limit: 5,
          offset: 0,
        });
      }
      return jsonResponse({});
    });

    renderPage();

    expect(
      await screen.findByRole("heading", { name: /панель наблюдаемости/i }),
    ).toBeDefined();
    expect(await screen.findByText(/vacancy:create/i)).toBeDefined();
    expect(await screen.findByText(/статус backend: ok/i)).toBeDefined();

    await i18n.changeLanguage("en");
    expect(
      await screen.findByRole("heading", { name: /observability dashboard/i }),
    ).toBeDefined();
    expect(await screen.findByText(/backend status: ok/i)).toBeDefined();
  });

  it("loads parsing and scoring status lookups over existing backend contracts", async () => {
    await i18n.changeLanguage("en");
    fetchMock.mockImplementation((input: RequestInfo | URL) => {
      const url = String(input);
      if (url.endsWith("/health")) {
        return jsonResponse({ status: "ok" });
      }
      if (url.includes("/api/v1/audit/events?")) {
        return jsonResponse({
          items: [],
          total: 0,
          limit: 5,
          offset: 0,
        });
      }
      if (url.includes("/api/v1/candidates/")) {
        if (url.includes("/cv/parsing-status")) {
          return jsonResponse({
            candidate_id: "11111111-1111-4111-8111-111111111111",
            document_id: "22222222-2222-4222-8222-222222222222",
            job_id: "33333333-3333-4333-8333-333333333333",
            status: "succeeded",
            attempt_count: 1,
            last_error: null,
            queued_at: "2026-03-19T08:00:00Z",
            started_at: "2026-03-19T08:01:00Z",
            finished_at: "2026-03-19T08:02:00Z",
            updated_at: "2026-03-19T08:03:00Z",
            analysis_ready: true,
            detected_language: "mixed",
          });
        }
      }
      if (url.includes("/api/v1/vacancies/") && url.includes("/match-scores/")) {
        return jsonResponse({
          vacancy_id: "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa",
          candidate_id: "11111111-1111-4111-8111-111111111111",
          status: "succeeded",
          score: 0.88,
          confidence: 0.61,
          requires_manual_review: true,
          manual_review_reason: "low_confidence",
          confidence_threshold: 0.75,
          summary: "Strong fit with limited confidence.",
          matched_requirements: [],
          missing_requirements: [],
          evidence: [],
          scored_at: "2026-03-19T10:00:00Z",
          model_name: "ollama",
          model_version: "1",
        });
      }
      return jsonResponse({});
    });

    renderPage();
    expect(
      await screen.findByRole("heading", { name: /observability dashboard/i }),
    ).toBeDefined();

    fireEvent.change(screen.getByLabelText(/candidate id for parsing/i), {
      target: { value: "11111111-1111-4111-8111-111111111111" },
    });
    fireEvent.click(screen.getByRole("button", { name: /load status/i }));

    expect(await screen.findByText(/status: succeeded/i)).toBeDefined();
    expect(await screen.findByText(/analysis ready: yes/i)).toBeDefined();

    fireEvent.change(screen.getByLabelText(/vacancy id for scoring/i), {
      target: { value: "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa" },
    });
    fireEvent.change(screen.getByLabelText(/candidate id for scoring/i), {
      target: { value: "11111111-1111-4111-8111-111111111111" },
    });
    fireEvent.click(screen.getByRole("button", { name: /load score/i }));

    expect(await screen.findByText(/score: 0\.88/i)).toBeDefined();
    expect(await screen.findByText(/manual review required: yes/i)).toBeDefined();
    expect(await screen.findByText(/low confidence/i)).toBeDefined();
  });

  it("renders a localized parsing error when the lookup fails", async () => {
    await i18n.changeLanguage("en");
    fetchMock.mockImplementation((input: RequestInfo | URL) => {
      const url = String(input);
      if (url.endsWith("/health")) {
        return jsonResponse({ status: "ok" });
      }
      if (url.includes("/api/v1/audit/events?")) {
        return jsonResponse({
          items: [],
          total: 0,
          limit: 5,
          offset: 0,
        });
      }
      if (url.includes("/api/v1/candidates/") && url.includes("/cv/parsing-status")) {
        return jsonResponse({ detail: "candidate_not_found" }, 404);
      }
      return jsonResponse({});
    });

    renderPage();
    expect(
      await screen.findByRole("heading", { name: /observability dashboard/i }),
    ).toBeDefined();

    fireEvent.change(screen.getByLabelText(/candidate id for parsing/i), {
      target: { value: "missing-candidate" },
    });
    fireEvent.click(screen.getByRole("button", { name: /load status/i }));

    expect(await screen.findByText(/кандидат не найден|candidate was not found/i)).toBeDefined();
    expect(captureExceptionMock).toHaveBeenCalledTimes(1);
  });
});

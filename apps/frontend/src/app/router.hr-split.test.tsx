import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { cleanup, render, screen } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { RouterProvider, createMemoryRouter } from "react-router-dom";

import "./i18n";
import { appRoutes } from "./router";

const fetchMock = vi.fn();
vi.stubGlobal("fetch", fetchMock);

const { setTagMock } = vi.hoisted(() => ({
  setTagMock: vi.fn(),
}));

vi.mock("@sentry/react", () => ({
  setTag: setTagMock,
}));

function renderWithPath(pathname: string) {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: { retry: false },
      mutations: { retry: false },
    },
  });
  const memoryRouter = createMemoryRouter(appRoutes, {
    initialEntries: [pathname],
  });
  render(
    <QueryClientProvider client={queryClient}>
      <RouterProvider router={memoryRouter} />
    </QueryClientProvider>,
  );
}

function jsonResponse(payload: unknown) {
  return new Response(JSON.stringify(payload), {
    status: 200,
    headers: { "Content-Type": "application/json" },
  });
}

describe("HR workspace split routes", () => {
  beforeEach(() => {
    window.localStorage.clear();
    window.localStorage.setItem("hrm_access_token", "token");
    window.localStorage.setItem("hrm_user_role", "hr");
    fetchMock.mockReset();
    setTagMock.mockReset();
    fetchMock.mockImplementation((input: RequestInfo | URL) => {
      const url = String(input);
      if (url.endsWith("/api/v1/auth/me")) {
        return Promise.resolve(
          jsonResponse({
            subject_id: "11111111-1111-4111-8111-111111111111",
            role: "hr",
            session_id: "22222222-2222-4222-8222-222222222222",
            access_token_expires_at: 1893456000,
          }),
        );
      }
      if (url.includes("/api/v1/vacancies")) {
        return Promise.resolve(jsonResponse({ items: [], total: 0, limit: 20, offset: 0 }));
      }
      if (url.includes("/api/v1/candidates")) {
        return Promise.resolve(jsonResponse({ items: [], total: 0, limit: 20, offset: 0 }));
      }
      if (url.includes("/api/v1/onboarding/runs?")) {
        return Promise.resolve(
          jsonResponse({
            items: [],
            total: 0,
            limit: 20,
            offset: 0,
            summary: {
              run_count: 0,
              total_tasks: 0,
              pending_tasks: 0,
              in_progress_tasks: 0,
              completed_tasks: 0,
              overdue_tasks: 0,
            },
          }),
        );
      }
      if (url.includes("/api/v1/referrals")) {
        return Promise.resolve(
          jsonResponse({ items: [], total: 0, limit: 50, offset: 0 }),
        );
      }
      return Promise.resolve(jsonResponse({}));
    });
  });

  afterEach(() => {
    cleanup();
  });

  it("renders the HR overview route", async () => {
    renderWithPath("/hr");

    expect(await screen.findByRole("heading", { name: /recruitment workspace/i })).toBeDefined();
    expect(await screen.findByRole("link", { name: /open vacancies|открыть вакансии/i })).toBeDefined();
  });

  it("renders the HR vacancies route", async () => {
    renderWithPath("/hr/vacancies");

    expect(
      await screen.findByRole("heading", { name: /vacancy workspace|workspace вакансий/i }),
    ).toBeDefined();
    expect(setTagMock).toHaveBeenCalledWith("route", "/hr");
  });

  it("renders the HR pipeline route", async () => {
    renderWithPath("/hr/pipeline");

    expect(
      await screen.findByRole("heading", { name: /pipeline workspace|workspace pipeline/i }),
    ).toBeDefined();
  });

  it("renders the HR interviews route", async () => {
    renderWithPath("/hr/interviews");

    expect(
      await screen.findByRole("heading", { name: /interview workspace|workspace интервью/i }),
    ).toBeDefined();
  });

  it("renders the HR offers route", async () => {
    renderWithPath("/hr/offers");

    expect(
      await screen.findByRole("heading", { name: /offer workspace|workspace офферов/i }),
    ).toBeDefined();
  });

  it("renders the HR referrals route", async () => {
    renderWithPath("/hr/referrals");

    expect(
      await screen.findByRole("heading", { name: /referral workspace|workspace рефералов/i }),
    ).toBeDefined();
  });
});

import { beforeEach, describe, expect, it, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { RouterProvider, createMemoryRouter } from "react-router-dom";

import "./i18n";
import { appRoutes } from "./router";

const fetchMock = vi.fn();
vi.stubGlobal("fetch", fetchMock);

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

describe("role route guard", () => {
  beforeEach(() => {
    window.localStorage.clear();
    fetchMock.mockReset();
    fetchMock.mockImplementation((input: RequestInfo | URL) => {
      const url = String(input);
      if (url.includes("/api/v1/accounting/workspace?")) {
        return Promise.resolve(jsonResponse({ items: [], total: 0, limit: 20, offset: 0 }));
      }
      if (url.endsWith("/api/v1/vacancies/manager-workspace")) {
        return Promise.resolve(
          jsonResponse({
            summary: {
              vacancy_count: 0,
              open_vacancy_count: 0,
              candidate_count: 0,
              active_interview_count: 0,
              upcoming_interview_count: 0,
            },
            items: [],
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
      return Promise.resolve(jsonResponse({}));
    });
  });

  it("redirects unauthorized user from /hr to access denied", async () => {
    renderWithPath("/hr");
    expect(await screen.findByText(/доступ запрещён/i)).toBeDefined();
  });

  it("allows hr user into /hr", async () => {
    window.localStorage.setItem("hrm_access_token", "token");
    window.localStorage.setItem("hrm_user_role", "hr");

    renderWithPath("/hr");
    expect(await screen.findByRole("heading", { name: /recruitment workspace/i })).toBeDefined();
  });

  it("allows manager user into /manager", async () => {
    window.localStorage.setItem("hrm_access_token", "token");
    window.localStorage.setItem("hrm_user_role", "manager");

    renderWithPath("/manager");
    expect(await screen.findByRole("heading", { name: /кабинет менеджера/i })).toBeDefined();
  });

  it("blocks manager user from /accountant", async () => {
    window.localStorage.setItem("hrm_access_token", "token");
    window.localStorage.setItem("hrm_user_role", "manager");

    renderWithPath("/accountant");
    expect(await screen.findByText(/нет прав для этого рабочего места/i)).toBeDefined();
  });

  it("allows accountant user into /accountant", async () => {
    window.localStorage.setItem("hrm_access_token", "token");
    window.localStorage.setItem("hrm_user_role", "accountant");

    renderWithPath("/accountant");
    expect(
      await screen.findByRole("heading", { name: /accountant workspace|кабинет бухгалтера/i }),
    ).toBeDefined();
  });
});

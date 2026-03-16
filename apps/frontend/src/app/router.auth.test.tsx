import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { cleanup, render, screen, waitFor } from "@testing-library/react";
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
  return memoryRouter;
}

describe("login route", () => {
  beforeEach(() => {
    window.localStorage.clear();
    fetchMock.mockReset();
  });

  afterEach(() => {
    cleanup();
  });

  it("renders /login page for unauthenticated user", async () => {
    renderWithPath("/login");
    expect(await screen.findByRole("heading", { name: /вход для сотрудников/i })).toBeDefined();
  });

  it("redirects already-authenticated user from /login to workspace", async () => {
    window.localStorage.setItem("hrm_access_token", "access-token");
    window.localStorage.setItem("hrm_refresh_token", "refresh-token");
    window.localStorage.setItem("hrm_user_role", "hr");
    fetchMock.mockImplementation((input: RequestInfo | URL) => {
      const url = String(input);
      if (url.endsWith("/api/v1/auth/me")) {
        return Promise.resolve(
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
      }
      if (url.includes("/api/v1/vacancies")) {
        return Promise.resolve(
          new Response(JSON.stringify({ items: [], total: 0, limit: 20, offset: 0 }), {
            status: 200,
            headers: { "Content-Type": "application/json" },
          }),
        );
      }
      if (url.includes("/api/v1/candidates")) {
        return Promise.resolve(
          new Response(JSON.stringify({ items: [], total: 0, limit: 20, offset: 0 }), {
            status: 200,
            headers: { "Content-Type": "application/json" },
          }),
        );
      }
      if (url.includes("/api/v1/onboarding/runs?")) {
        return Promise.resolve(
          new Response(
            JSON.stringify({
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
            {
              status: 200,
              headers: { "Content-Type": "application/json" },
            },
          ),
        );
      }
      return Promise.resolve(new Response(JSON.stringify({}), { status: 200 }));
    });

    const router = renderWithPath("/login");

    await waitFor(() => {
      expect(router.state.location.pathname).toBe("/");
    });
    await waitFor(() => {
      expect(fetchMock.mock.calls.some((call) => String(call[0]).endsWith("/api/v1/auth/me"))).toBe(true);
    });
  });

  it("redirects already-authenticated employee from /login to /employee", async () => {
    window.localStorage.setItem("hrm_access_token", "access-token");
    window.localStorage.setItem("hrm_refresh_token", "refresh-token");
    window.localStorage.setItem("hrm_user_role", "employee");
    fetchMock.mockImplementation((input: RequestInfo | URL) => {
      const url = String(input);
      if (url.endsWith("/api/v1/auth/me")) {
        return Promise.resolve(
          new Response(
            JSON.stringify({
              subject_id: "11111111-1111-1111-1111-111111111111",
              role: "employee",
              session_id: "22222222-2222-2222-2222-222222222222",
              access_token_expires_at: 1893456000,
            }),
            {
              status: 200,
              headers: { "Content-Type": "application/json" },
            },
          ),
        );
      }
      if (url.endsWith("/api/v1/employees/me/onboarding")) {
        return Promise.resolve(
          new Response(
            JSON.stringify({
              employee_id: "33333333-3333-4333-8333-333333333333",
              first_name: "Ada",
              last_name: "Lovelace",
              email: "ada@example.com",
              location: "Minsk",
              current_title: "Engineer",
              start_date: null,
              offer_terms_summary: null,
              onboarding_id: "44444444-4444-4444-8444-444444444444",
              onboarding_status: "started",
              onboarding_started_at: "2026-03-11T09:00:00Z",
              tasks: [],
            }),
            {
              status: 200,
              headers: { "Content-Type": "application/json" },
            },
          ),
        );
      }
      return Promise.resolve(new Response(JSON.stringify({}), { status: 200 }));
    });

    const router = renderWithPath("/login");

    await waitFor(() => {
      expect(router.state.location.pathname).toBe("/employee");
    });
    await waitFor(() => {
      expect(
        fetchMock.mock.calls.some((call) => String(call[0]).endsWith("/api/v1/employees/me/onboarding")),
      ).toBe(true);
    });
  });

  it("redirects already-authenticated manager from /login to manager workspace on /", async () => {
    window.localStorage.setItem("hrm_access_token", "access-token");
    window.localStorage.setItem("hrm_refresh_token", "refresh-token");
    window.localStorage.setItem("hrm_user_role", "manager");
    fetchMock.mockImplementation((input: RequestInfo | URL) => {
      const url = String(input);
      if (url.endsWith("/api/v1/auth/me")) {
        return Promise.resolve(
          new Response(
            JSON.stringify({
              subject_id: "11111111-1111-1111-1111-111111111111",
              role: "manager",
              session_id: "22222222-2222-2222-2222-222222222222",
              access_token_expires_at: 1893456000,
            }),
            {
              status: 200,
              headers: { "Content-Type": "application/json" },
            },
          ),
        );
      }
      if (url.endsWith("/api/v1/vacancies/manager-workspace")) {
        return Promise.resolve(
          new Response(
            JSON.stringify({
              summary: {
                vacancy_count: 0,
                open_vacancy_count: 0,
                candidate_count: 0,
                active_interview_count: 0,
                upcoming_interview_count: 0,
              },
              items: [],
            }),
            {
              status: 200,
              headers: { "Content-Type": "application/json" },
            },
          ),
        );
      }
      if (url.includes("/api/v1/accounting/workspace?")) {
        return Promise.resolve(
          new Response(JSON.stringify({ items: [], total: 0, limit: 20, offset: 0 }), {
            status: 200,
            headers: { "Content-Type": "application/json" },
          }),
        );
      }
      if (url.includes("/api/v1/onboarding/runs?")) {
        return Promise.resolve(
          new Response(
            JSON.stringify({
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
            {
              status: 200,
              headers: { "Content-Type": "application/json" },
            },
          ),
        );
      }
      return Promise.resolve(new Response(JSON.stringify({}), { status: 200 }));
    });

    const router = renderWithPath("/login");

    await waitFor(() => {
      expect(router.state.location.pathname).toBe("/");
    });
    await waitFor(() => {
      expect(
        fetchMock.mock.calls.some(
          (call) => String(call[0]).endsWith("/api/v1/vacancies/manager-workspace"),
        ),
      ).toBe(true);
    });
  });

  it("redirects already-authenticated accountant from /login to accountant workspace on /", async () => {
    window.localStorage.setItem("hrm_access_token", "access-token");
    window.localStorage.setItem("hrm_refresh_token", "refresh-token");
    window.localStorage.setItem("hrm_user_role", "accountant");
    fetchMock.mockImplementation((input: RequestInfo | URL) => {
      const url = String(input);
      if (url.endsWith("/api/v1/auth/me")) {
        return Promise.resolve(
          new Response(
            JSON.stringify({
              subject_id: "11111111-1111-1111-1111-111111111111",
              role: "accountant",
              session_id: "22222222-2222-2222-2222-222222222222",
              access_token_expires_at: 1893456000,
            }),
            {
              status: 200,
              headers: { "Content-Type": "application/json" },
            },
          ),
        );
      }
      if (url.includes("/api/v1/accounting/workspace?")) {
        return Promise.resolve(
          new Response(JSON.stringify({ items: [], total: 0, limit: 20, offset: 0 }), {
            status: 200,
            headers: { "Content-Type": "application/json" },
          }),
        );
      }
      return Promise.resolve(new Response(JSON.stringify({}), { status: 200 }));
    });

    const router = renderWithPath("/login");

    await waitFor(() => {
      expect(router.state.location.pathname).toBe("/");
    });
    await waitFor(() => {
      expect(
        fetchMock.mock.calls.some((call) =>
          String(call[0]).includes("/api/v1/accounting/workspace?"),
        ),
      ).toBe(true);
    });
  });

  it("redirects already-authenticated leader from /login to /leader", async () => {
    window.localStorage.setItem("hrm_access_token", "access-token");
    window.localStorage.setItem("hrm_refresh_token", "refresh-token");
    window.localStorage.setItem("hrm_user_role", "leader");
    fetchMock.mockImplementation((input: RequestInfo | URL) => {
      const url = String(input);
      if (url.endsWith("/api/v1/auth/me")) {
        return Promise.resolve(
          new Response(
            JSON.stringify({
              subject_id: "11111111-1111-1111-1111-111111111111",
              role: "leader",
              session_id: "22222222-2222-2222-2222-222222222222",
              access_token_expires_at: 1893456000,
            }),
            {
              status: 200,
              headers: { "Content-Type": "application/json" },
            },
          ),
        );
      }
      if (url.includes("/api/v1/reporting/kpi-snapshots?")) {
        return Promise.resolve(
          new Response(JSON.stringify({ period_month: "2026-03-01", metrics: [] }), {
            status: 200,
            headers: { "Content-Type": "application/json" },
          }),
        );
      }
      return Promise.resolve(new Response(JSON.stringify({}), { status: 200 }));
    });

    const router = renderWithPath("/login");

    await waitFor(() => {
      expect(router.state.location.pathname).toBe("/leader");
    });
    await waitFor(() => {
      expect(fetchMock.mock.calls.some((call) => String(call[0]).endsWith("/api/v1/auth/me"))).toBe(true);
    });
  });

  it("clears broken session and keeps /login open when me bootstrap fails", async () => {
    window.localStorage.setItem("hrm_access_token", "broken-access-token");
    window.localStorage.setItem("hrm_refresh_token", "refresh-token");
    window.localStorage.setItem("hrm_user_role", "hr");
    fetchMock.mockResolvedValue(
      new Response(JSON.stringify({ detail: "http_401" }), {
        status: 401,
        headers: { "Content-Type": "application/json" },
      }),
    );

    renderWithPath("/login");

    expect(await screen.findByRole("heading", { name: /вход для сотрудников/i })).toBeDefined();
    await waitFor(() => {
      expect(window.localStorage.getItem("hrm_access_token")).toBeNull();
      expect(window.localStorage.getItem("hrm_refresh_token")).toBeNull();
      expect(window.localStorage.getItem("hrm_user_role")).toBeNull();
    });
  });
});

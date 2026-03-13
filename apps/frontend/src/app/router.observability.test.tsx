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

describe("frontend observability route tags", () => {
  beforeEach(() => {
    window.localStorage.clear();
    fetchMock.mockReset();
    setTagMock.mockReset();
    fetchMock.mockImplementation((input: RequestInfo | URL) => {
      const url = String(input);
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
      if (url.includes("/api/v1/accounting/workspace?")) {
        return Promise.resolve(
          jsonResponse({
            items: [],
            total: 0,
            limit: 20,
            offset: 0,
          }),
        );
      }
      if (url.includes("/api/v1/vacancies")) {
        return Promise.resolve(
          jsonResponse({
            items: [],
            total: 0,
            limit: 20,
            offset: 0,
          }),
        );
      }
      if (url.includes("/api/v1/candidates")) {
        return Promise.resolve(
          jsonResponse({
            items: [],
            total: 0,
            limit: 20,
            offset: 0,
          }),
        );
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
      if (url.includes("/api/v1/employees/me/onboarding")) {
        return Promise.resolve(
          jsonResponse({
            employee_id: "11111111-1111-4111-8111-111111111111",
            first_name: "Ada",
            last_name: "Lovelace",
            email: "ada@example.com",
            location: "Minsk",
            current_title: "Engineer",
            start_date: null,
            offer_terms_summary: null,
            onboarding_id: "22222222-2222-4222-8222-222222222222",
            onboarding_status: "started",
            onboarding_started_at: "2026-03-11T09:00:00Z",
            tasks: [],
          }),
        );
      }
      return Promise.resolve(jsonResponse({}));
    });
  });

  afterEach(() => {
    cleanup();
  });

  it("tags the HR workspace route on /", async () => {
    window.localStorage.setItem("hrm_access_token", "token");
    window.localStorage.setItem("hrm_user_role", "hr");

    renderWithPath("/");

    expect(await screen.findByRole("heading", { name: /recruitment workspace/i })).toBeDefined();
    expect(setTagMock).toHaveBeenCalledWith("workspace", "hr");
    expect(setTagMock).toHaveBeenCalledWith("role", "hr");
    expect(setTagMock).toHaveBeenCalledWith("route", "/");
  });

  it("tags the manager workspace route on / with manager workspace", async () => {
    window.localStorage.setItem("hrm_access_token", "token");
    window.localStorage.setItem("hrm_user_role", "manager");

    renderWithPath("/");

    expect(await screen.findByRole("heading", { name: /кабинет менеджера/i })).toBeDefined();
    expect(setTagMock).toHaveBeenCalledWith("workspace", "manager");
    expect(setTagMock).toHaveBeenCalledWith("role", "manager");
    expect(setTagMock).toHaveBeenCalledWith("route", "/");
  });

  it("tags the accountant workspace route on /", async () => {
    window.localStorage.setItem("hrm_access_token", "token");
    window.localStorage.setItem("hrm_user_role", "accountant");

    renderWithPath("/");

    expect(
      await screen.findByRole("heading", { name: /accountant workspace|кабинет бухгалтера/i }),
    ).toBeDefined();
    expect(setTagMock).toHaveBeenCalledWith("workspace", "accountant");
    expect(setTagMock).toHaveBeenCalledWith("role", "accountant");
    expect(setTagMock).toHaveBeenCalledWith("route", "/");
  });

  it("tags the candidate workspace route on /candidate", async () => {
    renderWithPath("/candidate");

    expect(await screen.findByRole("heading", { name: /кабинет кандидата/i })).toBeDefined();
    expect(setTagMock).toHaveBeenCalledWith("workspace", "candidate");
    expect(setTagMock).toHaveBeenCalledWith("role", "anonymous");
    expect(setTagMock).toHaveBeenCalledWith("route", "/candidate");
  });

  it("tags the login route on /login", async () => {
    renderWithPath("/login");

    expect(await screen.findByRole("heading", { name: /вход для сотрудников/i })).toBeDefined();
    expect(setTagMock).toHaveBeenCalledWith("workspace", "auth");
    expect(setTagMock).toHaveBeenCalledWith("role", "anonymous");
    expect(setTagMock).toHaveBeenCalledWith("route", "/login");
  });

  it("tags the employee workspace route on /employee", async () => {
    window.localStorage.setItem("hrm_access_token", "token");
    window.localStorage.setItem("hrm_user_role", "employee");

    renderWithPath("/employee");

    expect(await screen.findByRole("heading", { name: /портал онбординга/i })).toBeDefined();
    expect(setTagMock).toHaveBeenCalledWith("workspace", "employee");
    expect(setTagMock).toHaveBeenCalledWith("role", "employee");
    expect(setTagMock).toHaveBeenCalledWith("route", "/employee");
  });
});

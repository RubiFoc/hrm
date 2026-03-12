import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { cleanup, render, screen } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";

import "../app/i18n";
import { ManagerWorkspacePage } from "./ManagerWorkspacePage";

const fetchMock = vi.fn();
vi.stubGlobal("fetch", fetchMock);

function renderManagerWorkspacePage() {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: { retry: false },
      mutations: { retry: false },
    },
  });
  render(
    <QueryClientProvider client={queryClient}>
      <ManagerWorkspacePage />
    </QueryClientProvider>,
  );
}

function jsonResponse(payload: unknown, status = 200): Promise<Response> {
  return Promise.resolve(
    new Response(JSON.stringify(payload), {
      status,
      headers: { "Content-Type": "application/json" },
    }),
  );
}

describe("ManagerWorkspacePage", () => {
  beforeEach(() => {
    window.localStorage.clear();
    fetchMock.mockReset();
    window.localStorage.setItem("hrm_access_token", "access-token");
    window.localStorage.setItem("hrm_user_role", "manager");
  });

  afterEach(() => {
    cleanup();
  });

  it("renders loading state while the manager overview is pending", async () => {
    fetchMock.mockImplementation(
      () =>
        new Promise<Response>(() => {
          // Keep the request pending to expose the loading state.
        }),
    );

    renderManagerWorkspacePage();

    expect(await screen.findByText(/загрузка кабинета менеджера/i)).toBeDefined();
  });

  it("renders empty state when no manager-visible vacancies exist", async () => {
    fetchMock.mockImplementation((input: RequestInfo | URL) => {
      const url = String(input);
      if (url.endsWith("/api/v1/vacancies/manager-workspace")) {
        return jsonResponse({
          summary: {
            vacancy_count: 0,
            open_vacancy_count: 0,
            candidate_count: 0,
            active_interview_count: 0,
            upcoming_interview_count: 0,
          },
          items: [],
        });
      }
      if (url.includes("/api/v1/onboarding/runs?")) {
        return jsonResponse({
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
        });
      }
      return jsonResponse({});
    });

    renderManagerWorkspacePage();

    expect(await screen.findByText(/нет назначенных вакансий/i)).toBeDefined();
    expect(fetchMock).toHaveBeenCalledWith(
      expect.stringContaining("/api/v1/vacancies/manager-workspace"),
      expect.any(Object),
    );
  });

  it("renders error state when manager overview request fails", async () => {
    fetchMock.mockImplementation((input: RequestInfo | URL) => {
      const url = String(input);
      if (url.endsWith("/api/v1/vacancies/manager-workspace")) {
        return jsonResponse({ detail: "unexpected_failure" }, 500);
      }
      if (url.includes("/api/v1/onboarding/runs?")) {
        return jsonResponse({
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
        });
      }
      return jsonResponse({});
    });

    renderManagerWorkspacePage();

    expect(await screen.findByText(/не удалось загрузить данные кабинета менеджера/i)).toBeDefined();
  });

  it("renders manager hiring snapshot together with embedded onboarding visibility", async () => {
    fetchMock.mockImplementation((input: RequestInfo | URL) => {
      const url = String(input);
      if (url.endsWith("/api/v1/vacancies/manager-workspace")) {
        return jsonResponse({
          summary: {
            vacancy_count: 1,
            open_vacancy_count: 1,
            candidate_count: 2,
            active_interview_count: 1,
            upcoming_interview_count: 1,
          },
          items: [
            {
              vacancy_id: "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa",
              title: "Platform Engineer",
              department: "Engineering",
              status: "open",
              hiring_manager_staff_id: "11111111-1111-4111-8111-111111111111",
              hiring_manager_login: "manager-alpha",
              candidate_count: 2,
              active_interview_count: 1,
              latest_activity_at: "2026-03-12T09:30:00Z",
              created_at: "2026-03-10T08:00:00Z",
              updated_at: "2026-03-12T08:30:00Z",
            },
          ],
        });
      }
      if (
        url.endsWith(
          "/api/v1/vacancies/aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa/manager-workspace/candidates",
        )
      ) {
        return jsonResponse({
          vacancy: {
            vacancy_id: "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa",
            title: "Platform Engineer",
            department: "Engineering",
            status: "open",
            hiring_manager_staff_id: "11111111-1111-4111-8111-111111111111",
            hiring_manager_login: "manager-alpha",
            candidate_count: 2,
            active_interview_count: 1,
            latest_activity_at: "2026-03-12T09:30:00Z",
            created_at: "2026-03-10T08:00:00Z",
            updated_at: "2026-03-12T08:30:00Z",
          },
          summary: {
            candidate_count: 2,
            active_interview_count: 1,
            upcoming_interview_count: 1,
            stage_counts: {
              applied: 0,
              screening: 1,
              shortlist: 1,
              interview: 0,
              offer: 0,
              hired: 0,
              rejected: 0,
            },
          },
          items: [
            {
              candidate_id: "bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb",
              first_name: "Grace",
              last_name: "Hopper",
              email: "grace@example.com",
              location: "Brest",
              current_title: "Staff Engineer",
              analysis_ready: false,
              years_experience: null,
              skills: [],
              stage: "shortlist",
              stage_updated_at: "2026-03-12T09:30:00Z",
              candidate_updated_at: "2026-03-12T09:10:00Z",
              interview_status: "awaiting_candidate_confirmation",
              interview_scheduled_start_at: "2026-03-13T11:00:00Z",
              interview_scheduled_end_at: "2026-03-13T12:00:00Z",
              interview_timezone: "Europe/Minsk",
            },
            {
              candidate_id: "cccccccc-cccc-4ccc-8ccc-cccccccccccc",
              first_name: "Ada",
              last_name: "Lovelace",
              email: "ada@example.com",
              location: "Minsk",
              current_title: "Backend Engineer",
              analysis_ready: true,
              years_experience: 6,
              skills: ["python", "systems design"],
              stage: "screening",
              stage_updated_at: "2026-03-12T08:50:00Z",
              candidate_updated_at: "2026-03-12T08:45:00Z",
              interview_status: null,
              interview_scheduled_start_at: null,
              interview_scheduled_end_at: null,
              interview_timezone: null,
            },
          ],
        });
      }
      if (url.includes("/api/v1/onboarding/runs?")) {
        return jsonResponse({
          items: [
            {
              onboarding_id: "dddddddd-dddd-4ddd-8ddd-dddddddddddd",
              employee_id: "eeeeeeee-eeee-4eee-8eee-eeeeeeeeeeee",
              first_name: "John",
              last_name: "Doe",
              email: "john@example.com",
              current_title: "Engineer",
              location: "Minsk",
              start_date: "2026-04-01",
              onboarding_status: "started",
              onboarding_started_at: "2026-03-11T09:00:00Z",
              total_tasks: 2,
              pending_tasks: 1,
              in_progress_tasks: 1,
              completed_tasks: 0,
              overdue_tasks: 0,
              progress_percent: 50,
            },
          ],
          total: 1,
          limit: 20,
          offset: 0,
          summary: {
            run_count: 1,
            total_tasks: 2,
            pending_tasks: 1,
            in_progress_tasks: 1,
            completed_tasks: 0,
            overdue_tasks: 0,
          },
        });
      }
      if (url.endsWith("/api/v1/onboarding/runs/dddddddd-dddd-4ddd-8ddd-dddddddddddd")) {
        return jsonResponse({
          onboarding_id: "dddddddd-dddd-4ddd-8ddd-dddddddddddd",
          employee_id: "eeeeeeee-eeee-4eee-8eee-eeeeeeeeeeee",
          first_name: "John",
          last_name: "Doe",
          email: "john@example.com",
          current_title: "Engineer",
          location: "Minsk",
          start_date: "2026-04-01",
          offer_terms_summary: "Laptop and access baseline.",
          onboarding_status: "started",
          onboarding_started_at: "2026-03-11T09:00:00Z",
          total_tasks: 2,
          pending_tasks: 1,
          in_progress_tasks: 1,
          completed_tasks: 0,
          overdue_tasks: 0,
          progress_percent: 50,
          tasks: [
            {
              task_id: "ffffffff-ffff-4fff-8fff-ffffffffffff",
              code: "manager_intro",
              title: "Manager intro",
              description: "Meet your manager",
              sort_order: 10,
              is_required: true,
              status: "in_progress",
              assigned_role: "manager",
              assigned_staff_id: null,
              due_at: "2026-03-13T09:00:00Z",
              completed_at: null,
              updated_at: "2026-03-11T09:00:00Z",
            },
          ],
        });
      }
      return jsonResponse({});
    });

    renderManagerWorkspacePage();

    expect(await screen.findByRole("heading", { name: /кабинет менеджера/i })).toBeDefined();
    expect(await screen.findByText(/platform engineer/i)).toBeDefined();
    expect(await screen.findByText(/grace hopper/i)).toBeDefined();
    expect(await screen.findByText(/manager intro/i)).toBeDefined();
  });
});

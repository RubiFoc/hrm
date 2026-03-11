import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";

import "../app/i18n";
import { OnboardingDashboardPage } from "./OnboardingDashboardPage";

const fetchMock = vi.fn();
vi.stubGlobal("fetch", fetchMock);

function renderOnboardingDashboardPage() {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: { retry: false },
      mutations: { retry: false },
    },
  });
  render(
    <QueryClientProvider client={queryClient}>
      <OnboardingDashboardPage />
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

describe("OnboardingDashboardPage", () => {
  beforeEach(() => {
    window.localStorage.clear();
    fetchMock.mockReset();
  });

  afterEach(() => {
    cleanup();
  });

  it("renders manager onboarding dashboard with summary and task detail", async () => {
    window.localStorage.setItem("hrm_access_token", "access-token");
    window.localStorage.setItem("hrm_user_role", "manager");

    fetchMock.mockImplementation((input: RequestInfo | URL) => {
      const url = String(input);
      if (url.includes("/api/v1/onboarding/runs?")) {
        return jsonResponse({
          items: [
            {
              onboarding_id: "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa",
              employee_id: "bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb",
              first_name: "Ada",
              last_name: "Lovelace",
              email: "ada@example.com",
              current_title: "Engineer",
              location: "Minsk",
              start_date: "2026-04-01",
              onboarding_status: "started",
              onboarding_started_at: "2026-03-11T09:00:00Z",
              total_tasks: 3,
              pending_tasks: 1,
              in_progress_tasks: 1,
              completed_tasks: 1,
              overdue_tasks: 1,
              progress_percent: 33,
            },
          ],
          total: 1,
          limit: 20,
          offset: 0,
          summary: {
            run_count: 1,
            total_tasks: 3,
            pending_tasks: 1,
            in_progress_tasks: 1,
            completed_tasks: 1,
            overdue_tasks: 1,
          },
        });
      }
      if (url.endsWith("/api/v1/onboarding/runs/aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa")) {
        return jsonResponse({
          onboarding_id: "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa",
          employee_id: "bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb",
          first_name: "Ada",
          last_name: "Lovelace",
          email: "ada@example.com",
          current_title: "Engineer",
          location: "Minsk",
          start_date: "2026-04-01",
          offer_terms_summary: "Laptop and access baseline.",
          onboarding_status: "started",
          onboarding_started_at: "2026-03-11T09:00:00Z",
          total_tasks: 3,
          pending_tasks: 1,
          in_progress_tasks: 1,
          completed_tasks: 1,
          overdue_tasks: 1,
          progress_percent: 33,
          tasks: [
            {
              task_id: "cccccccc-cccc-4ccc-8ccc-cccccccccccc",
              code: "manager_intro",
              title: "Manager intro",
              description: "Meet your manager",
              sort_order: 10,
              is_required: true,
              status: "in_progress",
              assigned_role: "manager",
              assigned_staff_id: null,
              due_at: "2026-03-12T09:00:00Z",
              completed_at: null,
              updated_at: "2026-03-11T09:00:00Z",
            },
          ],
        });
      }
      return jsonResponse({});
    });

    renderOnboardingDashboardPage();

    expect(await screen.findByRole("heading", { name: /прогресс онбординга/i })).toBeDefined();
    expect(await screen.findByText(/ada lovelace/i)).toBeDefined();
    expect(await screen.findByText(/manager intro/i)).toBeDefined();
    expect(fetchMock).toHaveBeenCalledWith(
      expect.stringContaining("/api/v1/onboarding/runs?"),
      expect.any(Object),
    );
  });

  it("applies task-status and overdue filters for the dashboard list request", async () => {
    window.localStorage.setItem("hrm_access_token", "access-token");
    window.localStorage.setItem("hrm_user_role", "manager");

    fetchMock.mockImplementation((input: RequestInfo | URL) => {
      const url = String(input);
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

    renderOnboardingDashboardPage();

    fireEvent.mouseDown(await screen.findByRole("combobox", { name: /статус задачи/i }));
    fireEvent.click(await screen.findByRole("option", { name: /завершено/i }));
    fireEvent.click(screen.getByLabelText(/только просроченные/i));

    await waitFor(() => {
      const calls = fetchMock.mock.calls.map((call) => String(call[0]));
      expect(
        calls.some(
          (url) =>
            url.includes("task_status=completed") && url.includes("overdue_only=true"),
        ),
      ).toBe(true);
    });
  });
});

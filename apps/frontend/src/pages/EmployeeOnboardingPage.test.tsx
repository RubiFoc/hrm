import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";

import "../app/i18n";
import { EmployeeOnboardingPage } from "./EmployeeOnboardingPage";

const fetchMock = vi.fn();
vi.stubGlobal("fetch", fetchMock);

const PORTAL_PAYLOAD = {
  employee_id: "11111111-1111-4111-8111-111111111111",
  first_name: "Ada",
  last_name: "Lovelace",
  email: "ada@example.com",
  location: "Minsk",
  current_title: "Engineer",
  start_date: null,
  offer_terms_summary: "Base salary 5000 BYN gross.",
  onboarding_id: "22222222-2222-4222-8222-222222222222",
  onboarding_status: "started",
  onboarding_started_at: "2026-03-11T09:00:00Z",
  tasks: [
    {
      task_id: "33333333-3333-4333-8333-333333333333",
      onboarding_id: "22222222-2222-4222-8222-222222222222",
      code: "accounts",
      title: "Create accounts",
      description: "Provision employee systems",
      sort_order: 10,
      is_required: true,
      status: "pending",
      assigned_role: "employee",
      assigned_staff_id: null,
      due_at: null,
      completed_at: null,
      created_at: "2026-03-11T09:00:00Z",
      updated_at: "2026-03-11T09:00:00Z",
      can_update: true,
    },
  ],
};

const DIRECTORY_PAYLOAD = {
  items: [
    {
      employee_id: "11111111-1111-4111-8111-111111111111",
      full_name: "Ada Lovelace",
      email: "ada@example.com",
      phone: "+375291234567",
      location: "Minsk",
      position_title: "Engineer",
      department: "R&D",
      manager: "Grace Hopper",
      subordinates: 0,
      birthday_day_month: "10-12",
      tenure_in_company_months: 12,
      avatar_url: null,
      avatar_updated_at: null,
      is_dismissed: false,
    },
  ],
  total: 1,
  limit: 20,
  offset: 0,
};

function renderEmployeeOnboardingPage() {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: { retry: false },
      mutations: { retry: false },
    },
  });
  render(
    <QueryClientProvider client={queryClient}>
      <EmployeeOnboardingPage />
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

describe("EmployeeOnboardingPage", () => {
  afterEach(() => {
    cleanup();
  });

  beforeEach(() => {
    window.localStorage.clear();
    window.localStorage.setItem("hrm_access_token", "employee-token");
    window.localStorage.setItem("hrm_user_role", "employee");
    fetchMock.mockReset();
  });

  it("renders onboarding portal and updates task status", async () => {
    fetchMock.mockImplementation((input: RequestInfo | URL, init?: RequestInit) => {
      const url = String(input);
      if (url.endsWith("/api/v1/employees/me/onboarding")) {
        return jsonResponse(PORTAL_PAYLOAD);
      }
      if (url.includes("/api/v1/employees/directory")) {
        return jsonResponse(DIRECTORY_PAYLOAD);
      }
      if (
        url.endsWith("/api/v1/employees/me/onboarding/tasks/33333333-3333-4333-8333-333333333333")
        && init?.method === "PATCH"
      ) {
        return jsonResponse({
          ...PORTAL_PAYLOAD.tasks[0],
          status: "in_progress",
          updated_at: "2026-03-11T10:00:00Z",
        });
      }
      return jsonResponse({});
    });

    renderEmployeeOnboardingPage();

    expect(await screen.findByRole("heading", { name: /портал онбординга/i })).toBeDefined();
    expect((await screen.findAllByText(/ada@example.com/i)).length).toBeGreaterThan(0);

    fireEvent.click(await screen.findByRole("button", { name: /начать задачу/i }));

    expect(await screen.findByText(/задача обновлена/i)).toBeDefined();
    expect(await screen.findByText(/в работе/i)).toBeDefined();
  });

  it("shows localized error when employee tries to update staff-managed task", async () => {
    fetchMock.mockImplementation((input: RequestInfo | URL, init?: RequestInit) => {
      const url = String(input);
      if (url.endsWith("/api/v1/employees/me/onboarding")) {
        return jsonResponse({
          ...PORTAL_PAYLOAD,
          tasks: [
            {
              ...PORTAL_PAYLOAD.tasks[0],
              task_id: "44444444-4444-4444-8444-444444444444",
              assigned_role: "hr",
              can_update: true,
            },
          ],
        });
      }
      if (url.includes("/api/v1/employees/directory")) {
        return jsonResponse(DIRECTORY_PAYLOAD);
      }
      if (
        url.endsWith("/api/v1/employees/me/onboarding/tasks/44444444-4444-4444-8444-444444444444")
        && init?.method === "PATCH"
      ) {
        return jsonResponse(
          { detail: "onboarding_task_not_actionable_by_employee" },
          409,
        );
      }
      return jsonResponse({});
    });

    renderEmployeeOnboardingPage();

    fireEvent.click(await screen.findByRole("button", { name: /начать задачу/i }));

    expect(
      await screen.findByText(/эта onboarding-задача сейчас управляется hr или другим исполнителем/i),
    ).toBeDefined();
  });
});

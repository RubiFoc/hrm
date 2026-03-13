import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";

import "../app/i18n";
import { NotificationsPanel } from "./NotificationsPanel";

const fetchMock = vi.fn();
vi.stubGlobal("fetch", fetchMock);

function renderNotificationsPanel(workspace: "manager" | "accountant" = "manager") {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: { retry: false },
      mutations: { retry: false },
    },
  });
  render(
    <QueryClientProvider client={queryClient}>
      <NotificationsPanel accessToken="access-token" workspace={workspace} />
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

describe("NotificationsPanel", () => {
  beforeEach(() => {
    fetchMock.mockReset();
  });

  afterEach(() => {
    cleanup();
  });

  it("renders unread notifications and marks one item as read", async () => {
    let isRead = false;
    fetchMock.mockImplementation((input: RequestInfo | URL) => {
      const url = String(input);
      if (url.endsWith("/api/v1/notifications/digest")) {
        return jsonResponse({
          generated_at: "2026-03-13T10:00:00Z",
          summary: {
            unread_notification_count: isRead ? 0 : 1,
            active_task_count: 2,
            overdue_task_count: 1,
            owned_open_vacancy_count: 1,
          },
          latest_unread_items: isRead
            ? []
            : [
                {
                  notification_id: "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa",
                  recipient_staff_id: "bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb",
                  recipient_role: "manager",
                  kind: "vacancy_assignment",
                  source_type: "vacancy",
                  source_id: "cccccccc-cccc-4ccc-8ccc-cccccccccccc",
                  status: "unread",
                  title: "Vacancy assigned: Platform Engineer",
                  body: "You were assigned as the hiring manager for Platform Engineer in Engineering.",
                  payload: {
                    vacancy_id: "cccccccc-cccc-4ccc-8ccc-cccccccccccc",
                    onboarding_id: null,
                    task_id: null,
                    employee_id: null,
                    vacancy_title: "Platform Engineer",
                    task_title: null,
                    employee_full_name: null,
                    due_at: null,
                  },
                  created_at: "2026-03-13T10:00:00Z",
                  read_at: null,
                },
              ],
        });
      }
      if (url.includes("/api/v1/notifications?")) {
        return jsonResponse({
          items: isRead
            ? []
            : [
                {
                  notification_id: "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa",
                  recipient_staff_id: "bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb",
                  recipient_role: "manager",
                  kind: "vacancy_assignment",
                  source_type: "vacancy",
                  source_id: "cccccccc-cccc-4ccc-8ccc-cccccccccccc",
                  status: "unread",
                  title: "Vacancy assigned: Platform Engineer",
                  body: "You were assigned as the hiring manager for Platform Engineer in Engineering.",
                  payload: {
                    vacancy_id: "cccccccc-cccc-4ccc-8ccc-cccccccccccc",
                    onboarding_id: null,
                    task_id: null,
                    employee_id: null,
                    vacancy_title: "Platform Engineer",
                    task_title: null,
                    employee_full_name: null,
                    due_at: null,
                  },
                  created_at: "2026-03-13T10:00:00Z",
                  read_at: null,
                },
              ],
          total: isRead ? 0 : 1,
          limit: 5,
          offset: 0,
          unread_count: isRead ? 0 : 1,
        });
      }
      if (url.endsWith("/api/v1/notifications/aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa/read")) {
        isRead = true;
        return jsonResponse({
          notification_id: "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa",
          recipient_staff_id: "bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb",
          recipient_role: "manager",
          kind: "vacancy_assignment",
          source_type: "vacancy",
          source_id: "cccccccc-cccc-4ccc-8ccc-cccccccccccc",
          status: "read",
          title: "Vacancy assigned: Platform Engineer",
          body: "You were assigned as the hiring manager for Platform Engineer in Engineering.",
          payload: {
            vacancy_id: "cccccccc-cccc-4ccc-8ccc-cccccccccccc",
            onboarding_id: null,
            task_id: null,
            employee_id: null,
            vacancy_title: "Platform Engineer",
            task_title: null,
            employee_full_name: null,
            due_at: null,
          },
          created_at: "2026-03-13T10:00:00Z",
          read_at: "2026-03-13T10:05:00Z",
        });
      }
      return jsonResponse({});
    });

    renderNotificationsPanel("manager");

    expect(await screen.findByText(/notifications|уведомления/i)).toBeDefined();
    expect(await screen.findByText(/vacancy assigned: platform engineer/i)).toBeDefined();
    expect(await screen.findByText(/open vacancies: 1|открытые вакансии: 1/i)).toBeDefined();

    fireEvent.click(screen.getByRole("button", { name: /mark as read|отметить как прочитанное/i }));

    await waitFor(() => {
      expect(
        fetchMock.mock.calls.some((call) =>
          String(call[0]).includes("/api/v1/notifications/aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa/read"),
        ),
      ).toBe(true);
    });
    expect(await screen.findByText(/you are all caught up|непрочитанных уведомлений нет/i)).toBeDefined();
  });

  it("renders accountant empty state without manager-only summary chip", async () => {
    fetchMock.mockImplementation((input: RequestInfo | URL) => {
      const url = String(input);
      if (url.endsWith("/api/v1/notifications/digest")) {
        return jsonResponse({
          generated_at: "2026-03-13T10:00:00Z",
          summary: {
            unread_notification_count: 0,
            active_task_count: 1,
            overdue_task_count: 0,
            owned_open_vacancy_count: 0,
          },
          latest_unread_items: [],
        });
      }
      if (url.includes("/api/v1/notifications?")) {
        return jsonResponse({
          items: [],
          total: 0,
          limit: 5,
          offset: 0,
          unread_count: 0,
        });
      }
      return jsonResponse({});
    });

    renderNotificationsPanel("accountant");

    expect(await screen.findByText(/notifications|уведомления/i)).toBeDefined();
    expect(await screen.findByText(/you are all caught up|непрочитанных уведомлений нет/i)).toBeDefined();
    expect(screen.queryByText(/open vacancies|открытые вакансии/i)).toBeNull();
  });
});

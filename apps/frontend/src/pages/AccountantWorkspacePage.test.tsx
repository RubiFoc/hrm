import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";

import "../app/i18n";
import { AccountantWorkspacePage } from "./AccountantWorkspacePage";

const fetchMock = vi.fn();
vi.stubGlobal("fetch", fetchMock);

function renderAccountantWorkspacePage() {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: { retry: false },
      mutations: { retry: false },
    },
  });
  render(
    <QueryClientProvider client={queryClient}>
      <AccountantWorkspacePage />
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

describe("AccountantWorkspacePage", () => {
  const createObjectUrlMock = vi.fn(() => "blob:accounting-export");
  const revokeObjectUrlMock = vi.fn();
  let clickSpy: ReturnType<typeof vi.spyOn>;

  beforeEach(() => {
    window.localStorage.clear();
    fetchMock.mockReset();
    createObjectUrlMock.mockReset();
    revokeObjectUrlMock.mockReset();
    window.localStorage.setItem("hrm_access_token", "access-token");
    window.localStorage.setItem("hrm_user_role", "accountant");
    window.URL.createObjectURL = createObjectUrlMock;
    window.URL.revokeObjectURL = revokeObjectUrlMock;
    clickSpy = vi.spyOn(HTMLAnchorElement.prototype, "click").mockImplementation(() => {});
  });

  afterEach(() => {
    cleanup();
    clickSpy.mockRestore();
  });

  it("renders accountant workspace rows and export actions", async () => {
    fetchMock.mockImplementation((input: RequestInfo | URL) => {
      const url = String(input);
      if (url.includes("/api/v1/accounting/workspace?")) {
        return jsonResponse({
          items: [
            {
              onboarding_id: "11111111-1111-4111-8111-111111111111",
              employee_id: "22222222-2222-4222-8222-222222222222",
              first_name: "Ada",
              last_name: "Adams",
              email: "ada@example.com",
              location: "Minsk",
              current_title: "Accountant Liaison",
              start_date: "2026-04-01",
              offer_terms_summary: "Payroll starter pack",
              onboarding_status: "started",
              accountant_task_total: 2,
              accountant_task_pending: 1,
              accountant_task_in_progress: 0,
              accountant_task_completed: 1,
              accountant_task_overdue: 1,
              latest_accountant_due_at: "2026-03-14T10:00:00Z",
            },
          ],
          total: 1,
          limit: 20,
          offset: 0,
        });
      }
      return jsonResponse({});
    });

    renderAccountantWorkspacePage();

    expect(
      await screen.findByRole("heading", {
        name: /accountant workspace|кабинет бухгалтера/i,
      }),
    ).toBeDefined();
    expect(await screen.findByText(/ada adams/i)).toBeDefined();
    expect(screen.getByRole("button", { name: /export csv|выгрузить csv/i })).toBeDefined();
    expect(
      screen.getByRole("button", { name: /export excel|выгрузить excel/i }),
    ).toBeDefined();
  });

  it("downloads CSV and XLSX exports for the full filtered scope", async () => {
    fetchMock.mockImplementation((input: RequestInfo | URL) => {
      const url = String(input);
      if (url.includes("/api/v1/accounting/workspace?")) {
        return jsonResponse({
          items: [],
          total: 0,
          limit: 20,
          offset: 0,
        });
      }
      if (url.includes("/api/v1/accounting/workspace/export?format=csv")) {
        return Promise.resolve(
          new Response("header\r\nvalue", {
            status: 200,
            headers: {
              "Content-Disposition":
                "attachment; filename=\"accounting-workspace-20260313T100000Z.csv\"",
              "Content-Type": "text/csv",
            },
          }),
        );
      }
      if (url.includes("/api/v1/accounting/workspace/export?format=xlsx")) {
        return Promise.resolve(
          new Response(new Uint8Array([80, 75, 3, 4]), {
            status: 200,
            headers: {
              "Content-Disposition":
                "attachment; filename=\"accounting-workspace-20260313T100000Z.xlsx\"",
              "Content-Type":
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            },
          }),
        );
      }
      return jsonResponse({});
    });

    renderAccountantWorkspacePage();
    await screen.findByRole("button", { name: /export csv|выгрузить csv/i });

    fireEvent.click(screen.getByRole("button", { name: /export csv|выгрузить csv/i }));
    await waitFor(() => {
      expect(
        fetchMock.mock.calls.some((call) =>
          String(call[0]).includes("/api/v1/accounting/workspace/export?format=csv"),
        ),
      ).toBe(true);
    });

    fireEvent.click(
      screen.getByRole("button", { name: /export excel|выгрузить excel/i }),
    );
    await waitFor(() => {
      expect(
        fetchMock.mock.calls.some((call) =>
          String(call[0]).includes("/api/v1/accounting/workspace/export?format=xlsx"),
        ),
      ).toBe(true);
    });
    expect(createObjectUrlMock).toHaveBeenCalledTimes(2);
    expect(revokeObjectUrlMock).toHaveBeenCalledTimes(2);
  });

  it("renders localized error state when accountant workspace request fails", async () => {
    fetchMock.mockImplementation((input: RequestInfo | URL) => {
      const url = String(input);
      if (url.includes("/api/v1/accounting/workspace?")) {
        return jsonResponse({ detail: "http_403" }, 403);
      }
      return jsonResponse({});
    });

    renderAccountantWorkspacePage();

    expect(
      await screen.findByText(
        /your account does not have accountant workspace access|нет доступа к accountant workspace/i,
      ),
    ).toBeDefined();
  });
});

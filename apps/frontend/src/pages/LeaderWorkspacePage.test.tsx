import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";

import "../app/i18n";
import { LeaderWorkspacePage } from "./LeaderWorkspacePage";

const fetchMock = vi.fn();
vi.stubGlobal("fetch", fetchMock);

function renderLeaderWorkspacePage() {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: { retry: false },
      mutations: { retry: false },
    },
  });
  render(
    <QueryClientProvider client={queryClient}>
      <LeaderWorkspacePage />
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

function shiftMonth(value: string, deltaMonths: number): string {
  const match = value.match(/^(\d{4})-(\d{2})$/);
  if (!match) {
    return value;
  }
  const year = Number(match[1]);
  const month = Number(match[2]);
  const shifted = new Date(Date.UTC(year, month - 1 + deltaMonths, 1));
  const shiftedYear = String(shifted.getUTCFullYear());
  const shiftedMonth = String(shifted.getUTCMonth() + 1).padStart(2, "0");
  return `${shiftedYear}-${shiftedMonth}`;
}

describe("LeaderWorkspacePage", () => {
  const createObjectUrlMock = vi.fn(() => "blob:kpi-export");
  const revokeObjectUrlMock = vi.fn();
  let clickSpy: ReturnType<typeof vi.spyOn>;

  beforeEach(() => {
    window.localStorage.clear();
    fetchMock.mockReset();
    createObjectUrlMock.mockReset();
    revokeObjectUrlMock.mockReset();
    window.localStorage.setItem("hrm_access_token", "access-token");
    window.localStorage.setItem("hrm_user_role", "leader");
    window.URL.createObjectURL = createObjectUrlMock;
    window.URL.revokeObjectURL = revokeObjectUrlMock;
    clickSpy = vi.spyOn(HTMLAnchorElement.prototype, "click").mockImplementation(() => {});
  });

  afterEach(() => {
    cleanup();
    clickSpy.mockRestore();
  });

  it("renders KPI snapshot metrics and export actions", async () => {
    fetchMock.mockImplementation((input: RequestInfo | URL) => {
      const url = String(input);
      if (url.includes("/api/v1/reporting/kpi-snapshots?period_month=")) {
        return jsonResponse({
          period_month: "2026-03-01",
          metrics: [
            {
              metric_key: "vacancies_created_count",
              metric_value: 3,
              generated_at: "2026-03-14T10:00:00Z",
            },
            {
              metric_key: "candidates_applied_count",
              metric_value: 5,
              generated_at: "2026-03-14T10:00:00Z",
            },
            {
              metric_key: "interviews_scheduled_count",
              metric_value: 4,
              generated_at: "2026-03-14T10:00:00Z",
            },
            {
              metric_key: "offers_sent_count",
              metric_value: 2,
              generated_at: "2026-03-14T10:00:00Z",
            },
            {
              metric_key: "offers_accepted_count",
              metric_value: 1,
              generated_at: "2026-03-14T10:00:00Z",
            },
            {
              metric_key: "hires_count",
              metric_value: 1,
              generated_at: "2026-03-14T10:00:00Z",
            },
            {
              metric_key: "onboarding_started_count",
              metric_value: 1,
              generated_at: "2026-03-14T10:00:00Z",
            },
            {
              metric_key: "onboarding_tasks_completed_count",
              metric_value: 8,
              generated_at: "2026-03-14T10:00:00Z",
            },
            {
              metric_key: "total_hr_operations_count",
              metric_value: 12,
              generated_at: "2026-03-14T10:00:00Z",
            },
            {
              metric_key: "automated_hr_operations_count",
              metric_value: 8,
              generated_at: "2026-03-14T10:00:00Z",
            },
            {
              metric_key: "automated_hr_operations_share_percent",
              metric_value: 66,
              generated_at: "2026-03-14T10:00:00Z",
            },
          ],
        });
      }
      return jsonResponse({});
    });

    renderLeaderWorkspacePage();

    expect(
      await screen.findByRole("heading", {
        name: /leader workspace|кабинет руководителя/i,
      }),
    ).toBeDefined();

    const metricLabels = await screen.findAllByText(/vacancies created|создано вакансий/i);
    expect(metricLabels.length).toBeGreaterThan(0);
    expect(
      (await screen.findAllByText(/total hr operations|всего hr операций/i)).length,
    ).toBeGreaterThan(0);
    expect(
      (await screen.findAllByText(/automated hr share|доля автоматизации/i)).length,
    ).toBeGreaterThan(0);
    expect(screen.getByRole("button", { name: /export csv|выгрузить csv/i })).toBeDefined();
    expect(
      screen.getByRole("button", { name: /export excel|выгрузить excel/i }),
    ).toBeDefined();
  });

  it("renders empty state when snapshot rows are missing", async () => {
    fetchMock.mockImplementation((input: RequestInfo | URL) => {
      const url = String(input);
      if (url.includes("/api/v1/reporting/kpi-snapshots?period_month=")) {
        return jsonResponse({
          period_month: "2026-03-01",
          metrics: [],
        });
      }
      return jsonResponse({});
    });

    renderLeaderWorkspacePage();

    expect(
      await screen.findByText(/no kpi snapshot rows are available|kpi snapshot отсутствует/i),
    ).toBeDefined();
  });

  it("auto-selects the latest available snapshot when the current month is missing", async () => {
    const now = new Date();
    const currentMonth = `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, "0")}`;
    const previousMonth = shiftMonth(currentMonth, -1);
    const currentPeriodMonth = `${currentMonth}-01`;
    const previousPeriodMonth = `${previousMonth}-01`;

    fetchMock.mockImplementation((input: RequestInfo | URL) => {
      const url = String(input);
      if (url.includes(`/api/v1/reporting/kpi-snapshots?period_month=${currentPeriodMonth}`)) {
        return jsonResponse({
          period_month: currentPeriodMonth,
          metrics: [],
        });
      }
      if (url.includes(`/api/v1/reporting/kpi-snapshots?period_month=${previousPeriodMonth}`)) {
        return jsonResponse({
          period_month: previousPeriodMonth,
          metrics: [
            {
              metric_key: "vacancies_created_count",
              metric_value: 1,
              generated_at: "2026-02-14T10:00:00Z",
            },
          ],
        });
      }
      return jsonResponse({});
    });

    renderLeaderWorkspacePage();

    const monthField = (await screen.findByLabelText(/period month|месяц/i)) as HTMLInputElement;
    await waitFor(() => {
      expect(monthField.value).toBe(previousMonth);
    });

    const metricLabels = await screen.findAllByText(/vacancies created|создано вакансий/i);
    expect(metricLabels.length).toBeGreaterThan(0);
    expect(
      await screen.findByText(/no snapshot for|нет kpi snapshot'а за/i),
    ).toBeDefined();
  });

  it("falls back to the latest available snapshot when loading a missing month explicitly", async () => {
    const now = new Date();
    const currentMonth = `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, "0")}`;
    const missingMonth = shiftMonth(currentMonth, -3);
    const fallbackMonth = shiftMonth(missingMonth, -1);
    const currentPeriodMonth = `${currentMonth}-01`;
    const missingPeriodMonth = `${missingMonth}-01`;
    const fallbackPeriodMonth = `${fallbackMonth}-01`;

    fetchMock.mockImplementation((input: RequestInfo | URL) => {
      const url = String(input);
      if (url.includes(`/api/v1/reporting/kpi-snapshots?period_month=${currentPeriodMonth}`)) {
        return jsonResponse({
          period_month: currentPeriodMonth,
          metrics: [
            {
              metric_key: "vacancies_created_count",
              metric_value: 10,
              generated_at: "2026-03-14T10:00:00Z",
            },
          ],
        });
      }
      if (url.includes(`/api/v1/reporting/kpi-snapshots?period_month=${missingPeriodMonth}`)) {
        return jsonResponse({
          period_month: missingPeriodMonth,
          metrics: [],
        });
      }
      if (url.includes(`/api/v1/reporting/kpi-snapshots?period_month=${fallbackPeriodMonth}`)) {
        return jsonResponse({
          period_month: fallbackPeriodMonth,
          metrics: [
            {
              metric_key: "vacancies_created_count",
              metric_value: 2,
              generated_at: "2026-02-14T10:00:00Z",
            },
          ],
        });
      }
      return jsonResponse({});
    });

    renderLeaderWorkspacePage();
    await screen.findByRole("button", { name: /load|загрузить/i });

    const monthField = (await screen.findByLabelText(/period month|месяц/i)) as HTMLInputElement;
    fireEvent.change(monthField, { target: { value: missingMonth } });
    fireEvent.click(screen.getByRole("button", { name: /load|загрузить/i }));

    await waitFor(() => {
      expect(monthField.value).toBe(fallbackMonth);
    });

    expect(
      await screen.findByText(/no snapshot for|нет kpi snapshot'а за/i),
    ).toBeDefined();

    expect(
      fetchMock.mock.calls.some((call) =>
        String(call[0]).includes(`/api/v1/reporting/kpi-snapshots?period_month=${missingPeriodMonth}`),
      ),
    ).toBe(true);
    expect(
      fetchMock.mock.calls.some((call) =>
        String(call[0]).includes(`/api/v1/reporting/kpi-snapshots?period_month=${fallbackPeriodMonth}`),
      ),
    ).toBe(true);
  });

  it("downloads CSV and XLSX exports for the selected month", async () => {
    fetchMock.mockImplementation((input: RequestInfo | URL) => {
      const url = String(input);
      if (url.includes("/api/v1/reporting/kpi-snapshots?period_month=")) {
        return jsonResponse({
          period_month: "2026-03-01",
          metrics: [
            {
              metric_key: "vacancies_created_count",
              metric_value: 0,
              generated_at: "2026-03-14T10:00:00Z",
            },
          ],
        });
      }
      if (url.includes("/api/v1/reporting/kpi-snapshots/export?format=csv")) {
        return Promise.resolve(
          new Response("metric_key,metric_value\r\nvacancies_created_count,0", {
            status: 200,
            headers: {
              "Content-Disposition":
                "attachment; filename=\"kpi-snapshot-2026-03-01-20260314T100000Z.csv\"",
              "Content-Type": "text/csv",
            },
          }),
        );
      }
      if (url.includes("/api/v1/reporting/kpi-snapshots/export?format=xlsx")) {
        return Promise.resolve(
          new Response(new Uint8Array([80, 75, 3, 4]), {
            status: 200,
            headers: {
              "Content-Disposition":
                "attachment; filename=\"kpi-snapshot-2026-03-01-20260314T100000Z.xlsx\"",
              "Content-Type":
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            },
          }),
        );
      }
      return jsonResponse({});
    });

    renderLeaderWorkspacePage();
    await screen.findByRole("button", { name: /export csv|выгрузить csv/i });

    fireEvent.click(screen.getByRole("button", { name: /export csv|выгрузить csv/i }));
    await waitFor(() => {
      expect(
        fetchMock.mock.calls.some((call) =>
          String(call[0]).includes("/api/v1/reporting/kpi-snapshots/export?format=csv"),
        ),
      ).toBe(true);
    });

    fireEvent.click(
      screen.getByRole("button", { name: /export excel|выгрузить excel/i }),
    );
    await waitFor(() => {
      expect(
        fetchMock.mock.calls.some((call) =>
          String(call[0]).includes("/api/v1/reporting/kpi-snapshots/export?format=xlsx"),
        ),
      ).toBe(true);
    });

    expect(createObjectUrlMock).toHaveBeenCalledTimes(2);
    expect(revokeObjectUrlMock).toHaveBeenCalledTimes(2);
  });

  it("renders localized error state when snapshot request fails", async () => {
    fetchMock.mockImplementation((input: RequestInfo | URL) => {
      const url = String(input);
      if (url.includes("/api/v1/reporting/kpi-snapshots?period_month=")) {
        return jsonResponse({ detail: "http_403" }, 403);
      }
      return jsonResponse({});
    });

    renderLeaderWorkspacePage();

    expect(
      await screen.findByText(
        /your account does not have access to kpi snapshots|нет доступа к kpi snapshot/i,
      ),
    ).toBeDefined();
  });

  it("approves a raise request from the leader compensation queue", async () => {
    fetchMock.mockImplementation((input: RequestInfo | URL) => {
      const url = String(input);
      if (url.includes("/api/v1/reporting/kpi-snapshots?period_month=")) {
        return jsonResponse({
          period_month: "2026-03-01",
          metrics: [
            {
              metric_key: "vacancies_created_count",
              metric_value: 1,
              generated_at: "2026-03-14T10:00:00Z",
            },
          ],
        });
      }
      if (url.includes("/api/v1/compensation/raises?status=awaiting_leader")) {
        return jsonResponse({
          items: [
            {
              request_id: "rrrrrrrr-rrrr-4rrr-8rrr-rrrrrrrrrrrr",
              employee_id: "22222222-2222-4222-8222-222222222222",
              requested_by_staff_id: "11111111-1111-4111-8111-111111111111",
              requested_at: "2026-04-01T10:00:00Z",
              effective_date: "2026-05-01",
              proposed_base_salary: 2500,
              currency: "BYN",
              status: "awaiting_leader",
              confirmation_count: 2,
              confirmation_quorum: 2,
              leader_decision_by_staff_id: null,
              leader_decision_at: null,
              leader_decision_note: null,
            },
          ],
          total: 1,
          limit: 50,
          offset: 0,
        });
      }
      if (
        url.includes(
          "/api/v1/compensation/raises/rrrrrrrr-rrrr-4rrr-8rrr-rrrrrrrrrrrr/approve",
        )
      ) {
        return jsonResponse({
          request_id: "rrrrrrrr-rrrr-4rrr-8rrr-rrrrrrrrrrrr",
          employee_id: "22222222-2222-4222-8222-222222222222",
          requested_by_staff_id: "11111111-1111-4111-8111-111111111111",
          requested_at: "2026-04-01T10:00:00Z",
          effective_date: "2026-05-01",
          proposed_base_salary: 2500,
          currency: "BYN",
          status: "approved",
          confirmation_count: 2,
          confirmation_quorum: 2,
          leader_decision_by_staff_id: "33333333-3333-4333-8333-333333333333",
          leader_decision_at: "2026-04-01T11:00:00Z",
          leader_decision_note: "Approved",
        });
      }
      return jsonResponse({});
    });

    renderLeaderWorkspacePage();

    const approveButton = await screen.findByRole("button", {
      name: /одобрить|approve/i,
    });
    fireEvent.click(approveButton);

    await waitFor(() => {
      expect(
        fetchMock.mock.calls.some((call) =>
          String(call[0]).includes(
            "/api/v1/compensation/raises/rrrrrrrr-rrrr-4rrr-8rrr-rrrrrrrrrrrr/approve",
          ),
        ),
      ).toBe(true);
    });
  });
});

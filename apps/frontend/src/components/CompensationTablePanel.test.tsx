import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";

import "../app/i18n";
import { CompensationTablePanel } from "./CompensationTablePanel";

const fetchMock = vi.fn();
vi.stubGlobal("fetch", fetchMock);

function renderPanel() {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: { retry: false },
      mutations: { retry: false },
    },
  });
  render(
    <QueryClientProvider client={queryClient}>
      <CompensationTablePanel
        accessToken="access-token"
        title="Compensation"
        showBonusForm
      />
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

describe("CompensationTablePanel", () => {
  beforeEach(() => {
    fetchMock.mockReset();
  });

  afterEach(() => {
    cleanup();
  });

  it("renders compensation rows and submits a bonus update", async () => {
    fetchMock.mockImplementation((input: RequestInfo | URL) => {
      const url = String(input);
      if (url.includes("/api/v1/compensation/table")) {
        return jsonResponse({
          items: [
            {
              employee_id: "11111111-1111-4111-8111-111111111111",
              full_name: "Ada Lovelace",
              department: "Engineering",
              position_title: "Engineer",
              currency: "BYN",
              base_salary: 2000,
              bonus_amount: null,
              bonus_period_month: null,
              salary_band_min: 1800,
              salary_band_max: 2600,
              band_alignment_status: "within_band",
              last_raise_effective_date: "2026-04-01",
              last_raise_status: "approved",
            },
          ],
          total: 1,
          limit: 100,
          offset: 0,
        });
      }
      if (url.includes("/api/v1/compensation/bonuses")) {
        return jsonResponse({
          bonus_id: "bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb",
          employee_id: "11111111-1111-4111-8111-111111111111",
          period_month: "2026-04-01",
          amount: 300,
          currency: "BYN",
          note: "April bonus",
          created_by_staff_id: "cccccccc-cccc-4ccc-8ccc-cccccccccccc",
          updated_by_staff_id: "cccccccc-cccc-4ccc-8ccc-cccccccccccc",
          created_at: "2026-04-01T10:00:00Z",
          updated_at: "2026-04-01T10:00:00Z",
        });
      }
      return jsonResponse({});
    });

    renderPanel();

    expect(await screen.findByText(/Ada Lovelace/i)).toBeDefined();

    fireEvent.mouseDown(screen.getByLabelText(/сотрудник|employee/i));
    fireEvent.click(await screen.findByRole("option", { name: /Ada Lovelace/i }));
    fireEvent.change(screen.getByLabelText(/месяц бонуса|bonus month/i), {
      target: { value: "2026-04" },
    });
    fireEvent.change(screen.getByLabelText(/сумма бонуса|bonus amount/i), {
      target: { value: "300" },
    });

    fireEvent.click(screen.getByRole("button", { name: /сохранить бонус|save bonus/i }));

    await waitFor(() => {
      expect(
        fetchMock.mock.calls.some((call) =>
          String(call[0]).includes("/api/v1/compensation/bonuses"),
        ),
      ).toBe(true);
    });

    expect(await screen.findByText(/бонус сохранён|bonus saved/i)).toBeDefined();
  });
});

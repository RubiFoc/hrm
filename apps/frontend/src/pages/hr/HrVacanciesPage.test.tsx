import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";

import "../../app/i18n";
import { HrVacanciesPage } from "./HrVacanciesPage";

const fetchMock = vi.fn();
vi.stubGlobal("fetch", fetchMock);

function renderHrVacanciesPage() {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: { retry: false },
      mutations: { retry: false },
    },
  });
  render(
    <QueryClientProvider client={queryClient}>
      <HrVacanciesPage />
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

describe("HrVacanciesPage", () => {
  beforeEach(() => {
    window.localStorage.clear();
    fetchMock.mockReset();
    window.localStorage.setItem("hrm_access_token", "access-token");
    window.localStorage.setItem("hrm_user_role", "hr");
  });

  afterEach(() => {
    cleanup();
  });

  it("creates a salary band for the selected vacancy", async () => {
    fetchMock.mockImplementation((input: RequestInfo | URL) => {
      const url = String(input);
      if (url.endsWith("/api/v1/vacancies")) {
        return jsonResponse({
          items: [
            {
              vacancy_id: "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa",
              title: "Platform Engineer",
              description: "Build platform",
              department: "Engineering",
              status: "open",
              hiring_manager_staff_id: null,
              hiring_manager_login: null,
              created_at: "2026-03-10T08:00:00Z",
              updated_at: "2026-03-12T08:30:00Z",
            },
          ],
          total: 1,
          limit: 20,
          offset: 0,
        });
      }
      if (url.includes("/api/v1/compensation/salary-bands?")) {
        return jsonResponse({ items: [] });
      }
      if (url.includes("/api/v1/compensation/salary-bands")) {
        return jsonResponse({
          band_id: "bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb",
          vacancy_id: "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa",
          band_version: 1,
          min_amount: 1800,
          max_amount: 2600,
          currency: "BYN",
          created_by_staff_id: "cccccccc-cccc-4ccc-8ccc-cccccccccccc",
          created_at: "2026-04-01T10:00:00Z",
        });
      }
      return jsonResponse({});
    });

    renderHrVacanciesPage();

    const selectButton = await screen.findByRole("button", {
      name: /выбрать|select/i,
    });
    fireEvent.click(selectButton);

    fireEvent.change(screen.getByLabelText(/минимум|minimum/i), {
      target: { value: "1800" },
    });
    fireEvent.change(screen.getByLabelText(/максимум|maximum/i), {
      target: { value: "2600" },
    });
    fireEvent.click(screen.getByRole("button", { name: /добавить диапазон|add band/i }));

    await waitFor(() => {
      expect(
        fetchMock.mock.calls.some((call) =>
          String(call[0]).includes("/api/v1/compensation/salary-bands"),
        ),
      ).toBe(true);
    });
  });
});

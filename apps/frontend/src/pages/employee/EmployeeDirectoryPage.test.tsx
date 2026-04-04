import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { cleanup, render, screen } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { MemoryRouter } from "react-router-dom";

import "../../app/i18n";
import { EmployeeDirectoryPage } from "./EmployeeDirectoryPage";

const fetchMock = vi.fn();
vi.stubGlobal("fetch", fetchMock);

const DIRECTORY_PAYLOAD = {
  items: [
    {
      employee_id: "11111111-1111-4111-8111-111111111111",
      full_name: "Ada Lovelace",
      department: "Engineering",
      position_title: "Platform Engineer",
      manager: "Grace Hopper",
      location: "Minsk",
      tenure_in_company: 12,
      subordinates: null,
      phone: null,
      email: null,
      birthday_day_month: null,
      avatar: null,
    },
  ],
  total: 1,
  limit: 20,
  offset: 0,
};

function renderDirectoryPage() {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: { retry: false },
      mutations: { retry: false },
    },
  });
  render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter>
        <EmployeeDirectoryPage />
      </MemoryRouter>
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

describe("EmployeeDirectoryPage", () => {
  afterEach(() => {
    cleanup();
  });

  beforeEach(() => {
    window.localStorage.clear();
    window.localStorage.setItem("hrm_access_token", "staff-token");
    window.localStorage.setItem("hrm_user_role", "manager");
    fetchMock.mockReset();
    fetchMock.mockImplementation((input: RequestInfo | URL) => {
      const url = String(input);
      if (url.includes("/api/v1/employees/directory")) {
        return jsonResponse(DIRECTORY_PAYLOAD);
      }
      return jsonResponse({});
    });
  });

  it("renders directory and shows hidden values for redacted fields", async () => {
    renderDirectoryPage();

    expect(await screen.findByRole("heading", { name: /каталог сотрудников/i })).toBeDefined();
    const hiddenValues = await screen.findAllByText(/скрыто/i);
    expect(hiddenValues.length).toBeGreaterThan(0);
  });
});

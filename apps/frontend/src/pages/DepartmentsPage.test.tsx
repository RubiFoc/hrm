import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import i18n from "i18next";
import { MemoryRouter } from "react-router-dom";

import "../app/i18n";
import { DepartmentsPage } from "./DepartmentsPage";

const fetchMock = vi.fn();
vi.stubGlobal("fetch", fetchMock);

function renderPage() {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: { retry: false },
      mutations: { retry: false },
    },
  });

  render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter>
        <DepartmentsPage />
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

function jsonResponse(body: unknown, status = 200): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "Content-Type": "application/json" },
  });
}

describe("DepartmentsPage", () => {
  afterEach(() => {
    cleanup();
  });

  beforeEach(async () => {
    window.localStorage.clear();
    fetchMock.mockReset();
    await i18n.changeLanguage("ru");
  });

  it("renders department list for staff", async () => {
    window.localStorage.setItem("hrm_access_token", "token");
    window.localStorage.setItem("hrm_user_role", "employee");

    fetchMock.mockImplementation((input: RequestInfo | URL) => {
      const url = String(input);
      if (url.includes("/api/v1/departments")) {
        return Promise.resolve(
          jsonResponse({
            items: [
              {
                department_id: "11111111-1111-4111-8111-111111111111",
                name: "Engineering",
                created_at: "2026-04-06T10:00:00Z",
                updated_at: "2026-04-06T11:00:00Z",
              },
            ],
            total: 1,
            limit: 20,
            offset: 0,
          }),
        );
      }
      return Promise.resolve(jsonResponse({}));
    });

    renderPage();

    expect(
      await screen.findByRole("heading", {
        name: /справочник департаментов|departments directory/i,
      }),
    ).toBeDefined();
    expect(await screen.findByText("Engineering")).toBeDefined();
  });

  it("allows admin to create a department", async () => {
    window.localStorage.setItem("hrm_access_token", "token");
    window.localStorage.setItem("hrm_user_role", "admin");

    fetchMock.mockImplementation((input: RequestInfo | URL, init?: RequestInit) => {
      const url = String(input);
      if (url.includes("/api/v1/departments") && init?.method === "POST") {
        return Promise.resolve(
          jsonResponse({
            department_id: "22222222-2222-4222-8222-222222222222",
            name: "Finance",
            created_at: "2026-04-06T10:00:00Z",
            updated_at: "2026-04-06T10:00:00Z",
          }),
        );
      }
      if (url.includes("/api/v1/departments")) {
        return Promise.resolve(
          jsonResponse({
            items: [],
            total: 0,
            limit: 20,
            offset: 0,
          }),
        );
      }
      return Promise.resolve(jsonResponse({}));
    });

    renderPage();

    fireEvent.change(
      await screen.findByLabelText(/department name|название департамента/i),
      {
        target: { value: "Finance" },
      },
    );
    fireEvent.click(screen.getByRole("button", { name: /создать|create/i }));

    await waitFor(() => {
      expect(fetchMock).toHaveBeenCalled();
    });
    expect(await screen.findByText(/департамент создан|department created/i)).toBeDefined();
  });
});

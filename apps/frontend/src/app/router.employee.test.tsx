import { beforeEach, describe, expect, it, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { RouterProvider, createMemoryRouter } from "react-router-dom";

import "./i18n";
import { appRoutes } from "./router";

const fetchMock = vi.fn();
vi.stubGlobal("fetch", fetchMock);

function renderWithPath(pathname: string) {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: { retry: false },
      mutations: { retry: false },
    },
  });
  const memoryRouter = createMemoryRouter(appRoutes, {
    initialEntries: [pathname],
  });
  render(
    <QueryClientProvider client={queryClient}>
      <RouterProvider router={memoryRouter} />
    </QueryClientProvider>,
  );
}

describe("employee route guard", () => {
  beforeEach(() => {
    window.localStorage.clear();
    fetchMock.mockReset();
    fetchMock.mockResolvedValue(
      new Response(
        JSON.stringify({
          employee_id: "11111111-1111-4111-8111-111111111111",
          first_name: "Ada",
          last_name: "Lovelace",
          email: "ada@example.com",
          location: "Minsk",
          current_title: "Engineer",
          start_date: null,
          offer_terms_summary: null,
          onboarding_id: "22222222-2222-4222-8222-222222222222",
          onboarding_status: "started",
          onboarding_started_at: "2026-03-11T09:00:00Z",
          tasks: [],
        }),
        {
          status: 200,
          headers: { "Content-Type": "application/json" },
        },
      ),
    );
  });

  it("redirects unauthorized user to access-denied", async () => {
    renderWithPath("/employee");
    expect(await screen.findByText(/доступ запрещён/i)).toBeDefined();
  });

  it("redirects non-employee user to forbidden path", async () => {
    window.localStorage.setItem("hrm_access_token", "token");
    window.localStorage.setItem("hrm_user_role", "hr");

    renderWithPath("/employee");
    expect(await screen.findByText(/нет прав для этого рабочего места/i)).toBeDefined();
  });

  it("allows employee user into /employee", async () => {
    window.localStorage.setItem("hrm_access_token", "token");
    window.localStorage.setItem("hrm_user_role", "employee");

    renderWithPath("/employee");
    expect(await screen.findByRole("heading", { name: /портал онбординга/i })).toBeDefined();
  });
});

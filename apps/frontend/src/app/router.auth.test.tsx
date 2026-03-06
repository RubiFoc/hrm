import { beforeEach, describe, expect, it, vi } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
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

describe("login route", () => {
  beforeEach(() => {
    window.localStorage.clear();
    fetchMock.mockReset();
  });

  it("renders /login page for unauthenticated user", async () => {
    renderWithPath("/login");
    expect(await screen.findByRole("heading", { name: /вход для сотрудников/i })).toBeDefined();
  });

  it("redirects already-authenticated user from /login to workspace", async () => {
    window.localStorage.setItem("hrm_access_token", "access-token");
    window.localStorage.setItem("hrm_refresh_token", "refresh-token");
    window.localStorage.setItem("hrm_user_role", "hr");
    fetchMock.mockResolvedValue(
      new Response(
        JSON.stringify({
          subject_id: "11111111-1111-1111-1111-111111111111",
          role: "hr",
          session_id: "22222222-2222-2222-2222-222222222222",
          access_token_expires_at: 1893456000,
        }),
        {
          status: 200,
          headers: { "Content-Type": "application/json" },
        },
      ),
    );

    renderWithPath("/login");

    expect(await screen.findByText("Vacancies")).toBeDefined();
  });

  it("clears broken session and keeps /login open when me bootstrap fails", async () => {
    window.localStorage.setItem("hrm_access_token", "broken-access-token");
    window.localStorage.setItem("hrm_refresh_token", "refresh-token");
    window.localStorage.setItem("hrm_user_role", "hr");
    fetchMock.mockResolvedValue(
      new Response(JSON.stringify({ detail: "http_401" }), {
        status: 401,
        headers: { "Content-Type": "application/json" },
      }),
    );

    renderWithPath("/login");

    expect(await screen.findByRole("heading", { name: /вход для сотрудников/i })).toBeDefined();
    await waitFor(() => {
      expect(window.localStorage.getItem("hrm_access_token")).toBeNull();
      expect(window.localStorage.getItem("hrm_refresh_token")).toBeNull();
      expect(window.localStorage.getItem("hrm_user_role")).toBeNull();
    });
  });
});

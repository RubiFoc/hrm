import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { cleanup, render, screen } from "@testing-library/react";
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

function jsonResponse(payload: unknown) {
  return new Response(JSON.stringify(payload), {
    status: 200,
    headers: { "Content-Type": "application/json" },
  });
}

describe("leader route guard", () => {
  beforeEach(() => {
    window.localStorage.clear();
    fetchMock.mockReset();
    fetchMock.mockImplementation(() =>
      Promise.resolve(jsonResponse({ period_month: "2026-03-01", metrics: [] })),
    );
  });

  afterEach(() => {
    cleanup();
  });

  it("redirects unauthorized user to access-denied", async () => {
    renderWithPath("/leader");
    expect(await screen.findByText(/доступ запрещён/i)).toBeDefined();
  });

  it("redirects non-leader user to forbidden path", async () => {
    window.localStorage.setItem("hrm_access_token", "token");
    window.localStorage.setItem("hrm_user_role", "hr");

    renderWithPath("/leader");
    expect(await screen.findByText(/нет прав для этого рабочего места/i)).toBeDefined();
  });

  it("allows leader user into leader workspace", async () => {
    window.localStorage.setItem("hrm_access_token", "token");
    window.localStorage.setItem("hrm_user_role", "leader");

    renderWithPath("/leader");
    expect(
      await screen.findByRole("heading", {
        name: /leader workspace|кабинет руководителя/i,
      }),
    ).toBeDefined();
  });

  it("allows admin user into leader workspace", async () => {
    window.localStorage.setItem("hrm_access_token", "token");
    window.localStorage.setItem("hrm_user_role", "admin");

    renderWithPath("/leader");
    expect(
      await screen.findByRole("heading", {
        name: /leader workspace|кабинет руководителя/i,
      }),
    ).toBeDefined();
  });
});

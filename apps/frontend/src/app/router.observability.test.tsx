import { beforeEach, describe, expect, it, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { RouterProvider, createMemoryRouter } from "react-router-dom";

import "./i18n";
import { appRoutes } from "./router";

const fetchMock = vi.fn();
vi.stubGlobal("fetch", fetchMock);

const { setTagMock } = vi.hoisted(() => ({
  setTagMock: vi.fn(),
}));

vi.mock("@sentry/react", () => ({
  setTag: setTagMock,
}));

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

describe("frontend observability route tags", () => {
  beforeEach(() => {
    window.localStorage.clear();
    fetchMock.mockReset();
    setTagMock.mockReset();
    fetchMock.mockImplementation((input: RequestInfo | URL) => {
      const url = String(input);
      if (url.includes("/api/v1/vacancies")) {
        return Promise.resolve(
          jsonResponse({
            items: [],
            total: 0,
            limit: 20,
            offset: 0,
          }),
        );
      }
      if (url.includes("/api/v1/candidates")) {
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
  });

  it("tags the HR workspace route on /", async () => {
    window.localStorage.setItem("hrm_access_token", "token");
    window.localStorage.setItem("hrm_user_role", "hr");

    renderWithPath("/");

    expect(await screen.findByRole("heading", { name: /recruitment workspace/i })).toBeDefined();
    expect(setTagMock).toHaveBeenCalledWith("workspace", "hr");
    expect(setTagMock).toHaveBeenCalledWith("role", "hr");
    expect(setTagMock).toHaveBeenCalledWith("route", "/");
  });

  it("tags the candidate workspace route on /candidate", async () => {
    renderWithPath("/candidate");

    expect(await screen.findByRole("heading", { name: /кабинет кандидата/i })).toBeDefined();
    expect(setTagMock).toHaveBeenCalledWith("workspace", "candidate");
    expect(setTagMock).toHaveBeenCalledWith("role", "anonymous");
    expect(setTagMock).toHaveBeenCalledWith("route", "/candidate");
  });

  it("tags the login route on /login", async () => {
    renderWithPath("/login");

    expect(await screen.findByRole("heading", { name: /вход для сотрудников/i })).toBeDefined();
    expect(setTagMock).toHaveBeenCalledWith("workspace", "auth");
    expect(setTagMock).toHaveBeenCalledWith("role", "anonymous");
    expect(setTagMock).toHaveBeenCalledWith("route", "/login");
  });
});

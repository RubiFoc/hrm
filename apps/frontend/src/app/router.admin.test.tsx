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

describe("admin route guard", () => {
  beforeEach(() => {
    window.localStorage.clear();
    fetchMock.mockReset();
    setTagMock.mockReset();
    fetchMock.mockImplementation(() =>
      new Response(
        JSON.stringify({
          items: [],
          total: 0,
          limit: 20,
          offset: 0,
        }),
        {
          status: 200,
          headers: { "Content-Type": "application/json" },
        },
      ),
    );
  });

  it("redirects unauthorized user to access-denied", async () => {
    renderWithPath("/admin");
    expect(await screen.findByText(/доступ запрещён/i)).toBeDefined();
  });

  it("redirects non-admin user to forbidden path", async () => {
    window.localStorage.setItem("hrm_access_token", "token");
    window.localStorage.setItem("hrm_user_role", "hr");

    renderWithPath("/admin");
    expect(await screen.findByText(/нет прав для этого рабочего места/i)).toBeDefined();
  });

  it("allows admin user into admin shell", async () => {
    window.localStorage.setItem("hrm_access_token", "token");
    window.localStorage.setItem("hrm_user_role", "admin");

    renderWithPath("/admin");
    expect(await screen.findByRole("heading", { name: /админ пространство/i })).toBeDefined();
  });

  it("allows admin user into /admin/staff and sets sentry route tag", async () => {
    window.localStorage.setItem("hrm_access_token", "token");
    window.localStorage.setItem("hrm_user_role", "admin");

    renderWithPath("/admin/staff");
    expect(await screen.findByRole("heading", { name: /управление сотрудниками/i })).toBeDefined();
    expect(setTagMock).toHaveBeenCalledWith("workspace", "admin");
    expect(setTagMock).toHaveBeenCalledWith("role", "admin");
    expect(setTagMock).toHaveBeenCalledWith("route", "/admin/staff");
  });

  it("allows admin user into /admin/candidates and sets sentry route tag", async () => {
    window.localStorage.setItem("hrm_access_token", "token");
    window.localStorage.setItem("hrm_user_role", "admin");

    renderWithPath("/admin/candidates");
    expect(await screen.findByRole("heading", { name: /консоль кандидатов/i })).toBeDefined();
    expect(setTagMock).toHaveBeenCalledWith("workspace", "admin");
    expect(setTagMock).toHaveBeenCalledWith("role", "admin");
    expect(setTagMock).toHaveBeenCalledWith("route", "/admin/candidates");
  });

  it("allows admin user into /admin/vacancies and sets sentry route tag", async () => {
    window.localStorage.setItem("hrm_access_token", "token");
    window.localStorage.setItem("hrm_user_role", "admin");

    renderWithPath("/admin/vacancies");
    expect(await screen.findByRole("heading", { name: /консоль вакансий/i })).toBeDefined();
    expect(setTagMock).toHaveBeenCalledWith("workspace", "admin");
    expect(setTagMock).toHaveBeenCalledWith("role", "admin");
    expect(setTagMock).toHaveBeenCalledWith("route", "/admin/vacancies");
  });

  it("allows admin user into /admin/pipeline and sets sentry route tag", async () => {
    window.localStorage.setItem("hrm_access_token", "token");
    window.localStorage.setItem("hrm_user_role", "admin");

    renderWithPath("/admin/pipeline");
    expect(await screen.findByRole("heading", { name: /консоль pipeline/i })).toBeDefined();
    expect(setTagMock).toHaveBeenCalledWith("workspace", "admin");
    expect(setTagMock).toHaveBeenCalledWith("role", "admin");
    expect(setTagMock).toHaveBeenCalledWith("route", "/admin/pipeline");
  });

  it("allows admin user into /admin/audit and sets sentry route tag", async () => {
    window.localStorage.setItem("hrm_access_token", "token");
    window.localStorage.setItem("hrm_user_role", "admin");

    renderWithPath("/admin/audit");
    expect(await screen.findByRole("heading", { name: /консоль аудита/i })).toBeDefined();
    expect(setTagMock).toHaveBeenCalledWith("workspace", "admin");
    expect(setTagMock).toHaveBeenCalledWith("role", "admin");
    expect(setTagMock).toHaveBeenCalledWith("route", "/admin/audit");
  });

  it("allows admin user into /admin/employee-keys and sets sentry route tag", async () => {
    window.localStorage.setItem("hrm_access_token", "token");
    window.localStorage.setItem("hrm_user_role", "admin");

    renderWithPath("/admin/employee-keys");
    expect(await screen.findByRole("heading", { name: /ключи регистрации сотрудников/i })).toBeDefined();
    expect(setTagMock).toHaveBeenCalledWith("workspace", "admin");
    expect(setTagMock).toHaveBeenCalledWith("role", "admin");
    expect(setTagMock).toHaveBeenCalledWith("route", "/admin/employee-keys");
  });
});

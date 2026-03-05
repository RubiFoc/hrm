import { beforeEach, describe, expect, it } from "vitest";
import { render, screen } from "@testing-library/react";
import { RouterProvider, createMemoryRouter } from "react-router-dom";

import "./i18n";
import { appRoutes } from "./router";

function renderWithPath(pathname: string) {
  const memoryRouter = createMemoryRouter(appRoutes, {
    initialEntries: [pathname],
  });
  render(<RouterProvider router={memoryRouter} />);
}

describe("admin route guard", () => {
  beforeEach(() => {
    window.localStorage.clear();
  });

  it("redirects unauthorized user to access-denied", async () => {
    renderWithPath("/admin");
    expect(await screen.findByText(/доступ в админ раздел запрещён/i)).toBeDefined();
  });

  it("redirects non-admin user to forbidden path", async () => {
    window.localStorage.setItem("hrm_access_token", "token");
    window.localStorage.setItem("hrm_user_role", "hr");

    renderWithPath("/admin");
    expect(await screen.findByText(/нет прав admin/i)).toBeDefined();
  });

  it("allows admin user into admin shell", async () => {
    window.localStorage.setItem("hrm_access_token", "token");
    window.localStorage.setItem("hrm_user_role", "admin");

    renderWithPath("/admin");
    expect(await screen.findByRole("heading", { name: /админ пространство/i })).toBeDefined();
  });
});

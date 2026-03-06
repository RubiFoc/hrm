import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { RouterProvider, createMemoryRouter } from "react-router-dom";

import "../app/i18n";
import { LoginPage } from "./LoginPage";

const fetchMock = vi.fn();
vi.stubGlobal("fetch", fetchMock);

function renderLoginPage() {
  const router = createMemoryRouter(
    [
      { path: "/login", element: <LoginPage /> },
      { path: "/admin", element: <div>ADMIN_WORKSPACE</div> },
      { path: "/", element: <div>HR_WORKSPACE</div> },
      { path: "/access-denied", element: <div>ACCESS_DENIED</div> },
    ],
    {
      initialEntries: ["/login"],
    },
  );
  render(<RouterProvider router={router} />);
}

describe("LoginPage", () => {
  afterEach(() => {
    cleanup();
  });

  beforeEach(() => {
    window.localStorage.clear();
    fetchMock.mockReset();
  });

  it("redirects to role workspace after successful login and me bootstrap", async () => {
    fetchMock.mockImplementation((input: RequestInfo | URL) => {
      const url = String(input);
      if (url.includes("/api/v1/auth/login")) {
        return Promise.resolve(
          new Response(
            JSON.stringify({
              access_token: "access-token",
              refresh_token: "refresh-token",
              token_type: "bearer",
              expires_in: 3600,
              session_id: "11111111-1111-1111-1111-111111111111",
            }),
            {
              status: 200,
              headers: { "Content-Type": "application/json" },
            },
          ),
        );
      }
      if (url.includes("/api/v1/auth/me")) {
        return Promise.resolve(
          new Response(
            JSON.stringify({
              subject_id: "22222222-2222-2222-2222-222222222222",
              role: "admin",
              session_id: "11111111-1111-1111-1111-111111111111",
              access_token_expires_at: 1893456000,
            }),
            {
              status: 200,
              headers: { "Content-Type": "application/json" },
            },
          ),
        );
      }
      return Promise.resolve(new Response("not-found", { status: 404 }));
    });

    renderLoginPage();

    fireEvent.change(screen.getByLabelText(/логин или email/i), {
      target: { value: "admin" },
    });
    fireEvent.change(screen.getByLabelText(/пароль/i), {
      target: { value: "strong-password" },
    });
    fireEvent.click(screen.getByRole("button", { name: /войти/i }));

    expect(await screen.findByText("ADMIN_WORKSPACE")).toBeDefined();
    expect(window.localStorage.getItem("hrm_access_token")).toBe("access-token");
    expect(window.localStorage.getItem("hrm_refresh_token")).toBe("refresh-token");
    expect(window.localStorage.getItem("hrm_user_role")).toBe("admin");
  });

  it("shows localized invalid-credentials message for 401", async () => {
    fetchMock.mockResolvedValue(
      new Response(JSON.stringify({ detail: "invalid_credentials" }), {
        status: 401,
        headers: { "Content-Type": "application/json" },
      }),
    );

    renderLoginPage();

    fireEvent.change(screen.getByLabelText(/логин или email/i), {
      target: { value: "staff" },
    });
    fireEvent.change(screen.getByLabelText(/пароль/i), {
      target: { value: "wrong" },
    });
    fireEvent.click(screen.getByRole("button", { name: /войти/i }));

    expect(await screen.findByText(/неверный логин или пароль/i)).toBeDefined();
  });

  it("shows localized field-validation message for 422", async () => {
    fetchMock.mockResolvedValue(
      new Response(JSON.stringify({ detail: "http_422" }), {
        status: 422,
        headers: { "Content-Type": "application/json" },
      }),
    );

    renderLoginPage();

    fireEvent.change(screen.getByLabelText(/логин или email/i), {
      target: { value: "staff" },
    });
    fireEvent.change(screen.getByLabelText(/пароль/i), {
      target: { value: "secret" },
    });
    fireEvent.click(screen.getByRole("button", { name: /войти/i }));

    expect(await screen.findByText(/ошибка валидации полей/i)).toBeDefined();
  });

  it("shows generic localized error for unexpected failures", async () => {
    fetchMock.mockResolvedValue(
      new Response(JSON.stringify({ detail: "http_500" }), {
        status: 500,
        headers: { "Content-Type": "application/json" },
      }),
    );

    renderLoginPage();

    fireEvent.change(screen.getByLabelText(/логин или email/i), {
      target: { value: "staff" },
    });
    fireEvent.change(screen.getByLabelText(/пароль/i), {
      target: { value: "secret" },
    });
    fireEvent.click(screen.getByRole("button", { name: /войти/i }));

    expect(await screen.findByText(/не удалось выполнить вход/i)).toBeDefined();
  });
});

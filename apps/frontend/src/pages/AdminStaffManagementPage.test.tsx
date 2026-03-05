import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import i18n from "i18next";

import "../app/i18n";
import { AdminStaffManagementPage } from "./AdminStaffManagementPage";

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
      <AdminStaffManagementPage />
    </QueryClientProvider>,
  );
}

function jsonResponse(body: unknown, status = 200): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "Content-Type": "application/json" },
  });
}

describe("AdminStaffManagementPage", () => {
  afterEach(() => {
    cleanup();
  });

  beforeEach(async () => {
    fetchMock.mockReset();
    await i18n.changeLanguage("ru");
  });

  it("renders list and supports RU/EN localization", async () => {
    fetchMock.mockResolvedValue(
      jsonResponse({
        items: [],
        total: 0,
        limit: 20,
        offset: 0,
      }),
    );

    renderPage();
    expect(await screen.findByRole("heading", { name: /управление сотрудниками/i })).toBeDefined();

    await i18n.changeLanguage("en");
    expect(await screen.findByRole("heading", { name: /staff management/i })).toBeDefined();
  });

  it("applies search filter and sends query params to list endpoint", async () => {
    fetchMock
      .mockResolvedValueOnce(
        jsonResponse({
          items: [],
          total: 0,
          limit: 20,
          offset: 0,
        }),
      )
      .mockResolvedValueOnce(
        jsonResponse({
          items: [
            {
              staff_id: "2fda35c8-ad04-4eaf-a81c-8f6f6688c0c8",
              login: "staff-search-result",
              email: "staff-search-result@example.com",
              role: "hr",
              is_active: true,
              created_at: "2026-03-05T10:00:00Z",
              updated_at: "2026-03-05T10:00:00Z",
            },
          ],
          total: 1,
          limit: 20,
          offset: 0,
        }),
      );

    renderPage();
    await screen.findByText(/по текущим фильтрам сотрудники не найдены/i);

    fireEvent.change(screen.getByLabelText(/поиск по login или email/i), {
      target: { value: "staff-search-result" },
    });
    fireEvent.click(screen.getByRole("button", { name: /применить/i }));

    expect(await screen.findByText("staff-search-result")).toBeDefined();

    const requestUrl = String(fetchMock.mock.calls[1][0]);
    expect(requestUrl).toContain("/api/v1/admin/staff?");
    expect(requestUrl).toContain("search=staff-search-result");
    expect(requestUrl).toContain("limit=20");
    expect(requestUrl).toContain("offset=0");
  });

  it("sends PATCH update and shows success message", async () => {
    fetchMock
      .mockResolvedValueOnce(
        jsonResponse({
          items: [
            {
              staff_id: "70c5e8df-6ccf-4582-9ce0-95a26f41e007",
              login: "target-user",
              email: "target-user@example.com",
              role: "hr",
              is_active: true,
              created_at: "2026-03-05T10:00:00Z",
              updated_at: "2026-03-05T10:00:00Z",
            },
          ],
          total: 1,
          limit: 20,
          offset: 0,
        }),
      )
      .mockResolvedValueOnce(
        jsonResponse({
          staff_id: "70c5e8df-6ccf-4582-9ce0-95a26f41e007",
          login: "target-user",
          email: "target-user@example.com",
          role: "hr",
          is_active: false,
          created_at: "2026-03-05T10:00:00Z",
          updated_at: "2026-03-05T10:05:00Z",
        }),
      )
      .mockResolvedValueOnce(
        jsonResponse({
          items: [
            {
              staff_id: "70c5e8df-6ccf-4582-9ce0-95a26f41e007",
              login: "target-user",
              email: "target-user@example.com",
              role: "hr",
              is_active: false,
              created_at: "2026-03-05T10:00:00Z",
              updated_at: "2026-03-05T10:05:00Z",
            },
          ],
          total: 1,
          limit: 20,
          offset: 0,
        }),
      );

    renderPage();
    await screen.findByText("target-user");

    const toggle = screen.getByRole("checkbox", { name: /активен/i });
    fireEvent.click(toggle);
    fireEvent.click(screen.getByRole("button", { name: /сохранить/i }));

    await waitFor(() => {
      expect(fetchMock).toHaveBeenCalledTimes(3);
    });

    const patchCall = fetchMock.mock.calls[1];
    expect(String(patchCall[0])).toContain("/api/v1/admin/staff/70c5e8df-6ccf-4582-9ce0-95a26f41e007");
    expect((patchCall[1] as RequestInit).method).toBe("PATCH");
    expect((patchCall[1] as RequestInit).body).toBe(JSON.stringify({ is_active: false }));
    expect(await screen.findByText(/данные сотрудника успешно обновлены/i)).toBeDefined();
  });

  it("maps 409 reason-code to localized error message", async () => {
    fetchMock
      .mockResolvedValueOnce(
        jsonResponse({
          items: [
            {
              staff_id: "fcb354a4-d41c-43d9-ab95-8e8b5d1de4ce",
              login: "guard-target",
              email: "guard-target@example.com",
              role: "admin",
              is_active: true,
              created_at: "2026-03-05T10:00:00Z",
              updated_at: "2026-03-05T10:00:00Z",
            },
          ],
          total: 1,
          limit: 20,
          offset: 0,
        }),
      )
      .mockResolvedValueOnce(jsonResponse({ detail: "last_admin_protection" }, 409));

    renderPage();
    await screen.findByText("guard-target");

    fireEvent.click(screen.getByRole("checkbox", { name: /активен/i }));
    fireEvent.click(screen.getByRole("button", { name: /сохранить/i }));

    expect(
      await screen.findByText(/последний активный admin должен оставаться активным/i),
    ).toBeDefined();
  });
});
